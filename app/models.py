from sqlalchemy import Column, Integer, String, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .db import Base

class ReportORM(Base):
    __tablename__ = "ai_report"
    id = Column(UUID(as_uuid=True), primary_key=True)
    one_line_summary = Column(Text)
    bullets = Column(ARRAY(Text))
    pages = Column(Integer)
    file_path = Column(Text)
    risks = relationship("RiskORM", back_populates="report", cascade="all,delete-orphan")
    clauses = relationship("ClauseORM", back_populates="report", cascade="all,delete-orphan")

class ClauseORM(Base):
    __tablename__ = "ai_report_clause"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("ai_report.id"))
    page = Column(Integer)
    text = Column(Text)
    start_pos = Column(Integer, nullable=True)
    end_pos = Column(Integer, nullable=True)
    report = relationship("ReportORM", back_populates="clauses")

class RiskORM(Base):
    __tablename__ = "ai_report_risk"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("ai_report.id"))
    clause_id = Column(Integer)  # ClauseORM.id (옵션: FK로 바꿔도 됨)
    type = Column(String(120))
    severity = Column(String(20))
    llm_verdict = Column(String(20))
    reason = Column(Text)
    rule_hits = Column(ARRAY(Text))
    evidence_ids = Column(ARRAY(Integer))
    report = relationship("ReportORM", back_populates="risks")
