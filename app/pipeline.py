# E2E 파이프라인

import os
from typing import Dict
from dotenv import load_dotenv
from .utils_pdf import pdf_to_pages
from .splitters import split_into_clauses
from .risk_engine import summarize_with_evidence, risk_decision
from .storage import save_report
from .models import Report, Clause, Summary

# app/pipeline.py (발췌)
from fastapi import HTTPException

load_dotenv()

def analyze_pdf(doc_id: str, pdf_path: str) -> Dict:
    max_pages = int(os.getenv("MAX_PAGES_PER_DOC", "50"))
    pages = pdf_to_pages(pdf_path, max_pages=max_pages)

    if not pages:
        # OCR 실패 / 빈 PDF 등
        raise HTTPException(status_code=422, detail="PDF에서 텍스트를 추출하지 못했습니다. (스캔본이면 OCR 설정 확인)")

    clauses_text = split_into_clauses(pages)
    if not clauses_text:
        raise HTTPException(status_code=422, detail="조항 분할에 실패했습니다. 분할 규칙을 보강해 주세요.")

    clauses_text = split_into_clauses(pages)
    clauses = [Clause(id=i, text=t, page=0) for i, t in enumerate(clauses_text)]

    summary_dict = summarize_with_evidence(clauses_text)
    risks_dicts = risk_decision(clauses_text)

    report = Report(
        doc_id=doc_id,
        summary=Summary(**summary_dict),
        risks=[r for r in risks_dicts],
        clauses=clauses,
        meta={"pages": len(pages), "file_path": pdf_path},
    )
    save_report(doc_id, report.model_dump())
    return report.model_dump()
