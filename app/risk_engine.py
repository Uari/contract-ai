# app/risk_engine.py
from typing import List, Dict
from .rules import apply_rules

# -------------------------------------------------
# 1) 리스크 타입별 기본 심각도 & 설명 매핑
#    - 실제 운영 중 오탐/미탐을 보며 튜닝하세요.
# -------------------------------------------------
SEVERITY_BY_TYPE: Dict[str, str] = {
    # 공통
    "liability": "high",
    "jurisdiction": "watch",
    "nda": "watch",
    "sla": "medium",

    # 임대차 전용
    "lease_deposit": "high",       # 보증금 미반환/상계불가 등은 임차인 리스크 큼
    "lease_rent": "medium",
    "lease_repair": "medium",
    "lease_termination": "medium",
    "lease_sublease": "watch",
    "lease_restore": "medium",
    "lease_penalty": "high",       # 과도한 위약벌/지연손해금
    "lease_utilities": "watch",
    "lease_insurance": "watch",
    "lease_access": "watch",
}

DESCRIPTION_BY_TYPE: Dict[str, str] = {
    "liability": "손해배상 한도 부재/과도한 면책 등으로 과도한 책임이 전가될 수 있습니다.",
    "jurisdiction": "전속관할/불리한 관할 지정으로 분쟁 시 임차인/을이 불리할 수 있습니다.",
    "nda": "무기한 비밀유지, 광범위한 3자 제공 금지 등 과도한 의무가 있을 수 있습니다.",
    "sla": "과도한 가동률·위약 조항으로 불리한 배상 트리거가 설정될 수 있습니다.",

    "lease_deposit": "보증금 미반환/상계불가/지연이자 과다 등 임차인 보증금 보호에 불리합니다.",
    "lease_rent": "연체이자 과다·일할계산 배제 등 임차인 불리한 차임 규정일 수 있습니다.",
    "lease_repair": "수선·하자 책임이 포괄적으로 임차인에게 전가되어 있을 수 있습니다.",
    "lease_termination": "중도해지 불가·일방 해지·과도한 위약금 등 불리한 해지 조건입니다.",
    "lease_sublease": "전대/양도 전면 금지, 권리금 회수 방해 면책 등 임차인에게 불리합니다.",
    "lease_restore": "원상복구 범위가 과도하게 넓게 정의되었을 수 있습니다.",
    "lease_penalty": "위약벌·지연손해금이 과도하게 책정되어 있을 수 있습니다.",
    "lease_utilities": "관리비/공과금 산정 기준 불명확 또는 광범위한 부담 전가일 수 있습니다.",
    "lease_insurance": "보험 가입 의무/면책 구조가 과도하여 임차인 부담이 큽니다.",
    "lease_access": "사전 통지 없이 임대인 수시 출입 등 과도한 출입권이 설정되어 있을 수 있습니다.",
}

# -------------------------------------------------
# 2) 요약 훅 (LLM 미사용: 간단 요약)
#    - LLM 연결 시 이 함수만 교체하면 됩니다.
# -------------------------------------------------
def summarize_with_evidence(clauses: List[str]) -> Dict:
    bullets = []
    for i, c in enumerate(clauses[:5]):
        bullets.append(f"- {c[:100]}... [evidence:{i}]")
    return {"one_line": "초안 요약(LLM 연결 전)", "bullets": bullets}

def llm_verdict_stub(clause_text: str) -> str:
    # 실제 LLM 사용 시: 체크리스트 프롬프트 → JSON 파싱
    return "pending"

# -------------------------------------------------
# 3) 룰 매칭 → 심각도/설명 부여 → 리스크 결과화
# -------------------------------------------------
def risk_decision(clauses: List[str]):
    rule_hits = apply_rules(clauses)

    risks = []
    for h in rule_hits:
        rtype = h["type"]
        severity = SEVERITY_BY_TYPE.get(rtype, "watch")
        description = DESCRIPTION_BY_TYPE.get(rtype, "규정이 불리할 수 있는 신호입니다.")
        clause_id = h["clause_id"]

        risks.append({
            "type": rtype,
            "severity": severity,
            "rule_hits": [h["pattern"]],
            "llm_verdict": llm_verdict_stub(clauses[clause_id]),
            "reason": description,                # ← 설명
            "evidence_ids": [clause_id],         # ← 근거 조항 인덱스
        })

    # (옵션) 같은 타입/같은 clause_id 중복 합치기
    risks = _dedupe_risks(risks)
    return risks

def _dedupe_risks(risks: List[Dict]) -> List[Dict]:
    """같은 (type, clause_id)의 결과를 병합해서 rule_hits만 합칩니다."""
    merged = {}
    for r in risks:
        key = (r["type"], tuple(r["evidence_ids"]))
        if key not in merged:
            merged[key] = r
        else:
            merged[key]["rule_hits"] = list(set(merged[key]["rule_hits"] + r["rule_hits"]))
    return list(merged.values())
