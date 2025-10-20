# app/pipeline.py
# E2E 파이프라인

import os
import logging
from typing import Dict
from uuid import UUID
from dotenv import load_dotenv
from fastapi import HTTPException

from .utils_pdf import pdf_to_pages
from .splitters import split_into_clauses
from .risk_engine import summarize_with_evidence, risk_decision
from .storage import save_report
from .schemas import Report, Clause, Summary
from .db import SessionLocal
from .models import ReportORM, ClauseORM, RiskORM

load_dotenv()

logger = logging.getLogger(__name__)


def analyze_pdf(doc_id: str, pdf_path: str) -> Dict:
    """PDF → 페이지 텍스트 → 조항 분할 → 요약/리스크 → Report 생성+저장"""
    max_pages = int(os.getenv("MAX_PAGES_PER_DOC", "50"))
    pages = pdf_to_pages(pdf_path, max_pages=max_pages)

    if not pages:
        raise HTTPException(
            status_code=422,
            detail="PDF에서 텍스트를 추출하지 못했습니다. (스캔본이면 OCR 설정 확인)"
        )

    # ✅ 중복 호출 제거
    clauses_text = split_into_clauses(pages)
    if not clauses_text:
        raise HTTPException(
            status_code=422,
            detail="조항 분할에 실패했습니다. 분할 규칙을 보강해 주세요."
        )

    clauses = [Clause(id=i, text=t, page=0) for i, t in enumerate(clauses_text)]

    summary_dict = summarize_with_evidence(clauses_text)
    risks_dicts = risk_decision(clauses_text)   # dict 리스트 반환 → Pydantic이 검증/캐스팅

    report = Report(
        doc_id=doc_id,
        summary=Summary(**summary_dict),
        risks=[r for r in risks_dicts],
        clauses=clauses,
        meta={"pages": len(pages), "file_path": pdf_path},
    )

    # 파일 저장
    save_report(report.doc_id, report.model_dump())
    
    # DB 저장 (설정되어 있지 않으면 스킵)
    save_report_to_db(report)

    return report.model_dump()


def save_report_to_db(report: Report) -> None:
    """Pydantic Report → ORM 저장. Postgres(ARRAY) 기준."""
    # DB 미연결 시 안전 스킵
    if SessionLocal is None:
        logger.warning("DATABASE_URL not set or DB session not initialized. Skip saving.")
        return

    # ORM의 id가 UUID 컬럼이면 문자열을 UUID로 변환
    try:
        rid = UUID(str(report.doc_id))
    except Exception as e:
        logger.error(f"UUID 변환 실패: {e}")
        raise ValueError("report.doc_id는 UUID 형식이어야 합니다.")

    db = SessionLocal()
    try:
        # 상단 Report
        r = ReportORM(
            id=rid,
            one_line_summary=report.summary.one_line,
            bullets=report.summary.bullets,   # ARRAY(Text) → Postgres 필요
            pages=report.meta.pages,
            file_path=report.meta.file_path
        )
        db.add(r)
        db.flush()  # PK 확정

        # Clauses
        for c in report.clauses:
            db.add(ClauseORM(
                report_id=rid,
                page=c.page,
                text=c.text,
                start_pos=c.start,
                end_pos=c.end
            ))

        # Risks
        for k in report.risks:
            db.add(RiskORM(
                report_id=rid,
                clause_id=(k.evidence_ids[0] if k.evidence_ids else None),
                type=k.type,
                severity=k.severity,
                llm_verdict=k.llm_verdict,   # 'risky|watch|ok|pending' 준수
                reason=k.reason,
                rule_hits=k.rule_hits,       # ARRAY(Text)
                evidence_ids=k.evidence_ids  # ARRAY(Integer)
            ))

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"DB 저장 실패: {e}")
        raise
    finally:
        db.close()
