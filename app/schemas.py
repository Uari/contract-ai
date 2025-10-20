# app/schemas.py
from typing import List, Optional, Literal
from pydantic import BaseModel
from uuid import UUID

class Clause(BaseModel):
    id: int
    text: str
    page: Optional[int] = None
    start: Optional[int] = None
    end: Optional[int] = None

class Summary(BaseModel):
    one_line: str
    bullets: List[str]

class RiskItem(BaseModel):
    type: str
    severity: Literal["watch", "medium", "high"] | str  # 규칙 엔진 기본 단계 사용
    rule_hits: List[str]
    llm_verdict: Literal["risky", "watch", "ok", "pending"]
    reason: str
    evidence_ids: List[int]

class Meta(BaseModel):
    pages: int
    file_path: str

class Report(BaseModel):
    # 업로드 단계에서는 문자열 UUID가 들어오므로 str | UUID 모두 허용
    doc_id: str | UUID
    summary: Summary
    risks: List[RiskItem]
    clauses: List[Clause]
    meta: Meta

UploadResponse = Report  # 업로드 응답은 Report 스키마와 동일
__all__ = ["Report", "Clause", "Summary", "RiskItem", "Meta", "UploadResponse"]