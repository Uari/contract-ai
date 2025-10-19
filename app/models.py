from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from uuid import UUID

Severity = Literal["high", "medium", "low", "watch"]
Verdict = Literal["risky", "watch", "ok", "pending"]

class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    pages: int

class Clause(BaseModel):
    id: int
    text: str
    page: int
    start: Optional[int] = None
    end: Optional[int] = None

class RiskItem(BaseModel):
    type: str
    severity: Severity
    rule_hits: List[str] = []
    llm_verdict: Verdict = "pending"
    reason: Optional[str] = None
    evidence_ids: List[int] = []

class Summary(BaseModel):
    one_line: str
    bullets: List[str]

class Report(BaseModel):
    doc_id: str
    summary: Summary
    risks: List[RiskItem]
    clauses: List[Clause]
    meta: dict = Field(default_factory=dict)
