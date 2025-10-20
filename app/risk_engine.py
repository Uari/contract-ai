# app/risk_engine.py
import os, json, http.client, time, unicodedata, re
from typing import List, Dict
from .rules import apply_rules
from .llm_client_gemini import gemini_batch_verdicts

# ==== 1) 리스크 기본 매핑(그대로 사용/보강 가능) ====
SEVERITY_BY_TYPE: Dict[str, str] = {
    "liability": "high", "jurisdiction": "watch", "nda": "watch", "sla": "medium",
    "lease_deposit": "high", "lease_rent": "medium", "lease_repair": "medium",
    "lease_termination": "medium", "lease_sublease": "watch", "lease_restore": "medium",
    "lease_penalty": "high", "lease_utilities": "watch", "lease_insurance": "watch",
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
    "lease_access": "사전 통지 없이 임대인 수시 출입 등 과도한 출입권이 설정될 수 있습니다.",
}

# ==== 2) 유틸 ====
def _normalize_ko(s: str) -> str:
    return (s or "").replace("\u00A0"," ").strip()

def summarize_with_evidence(clauses: List[str]) -> Dict:
    bullets = [f"- {c[:100]}... [evidence:{i}]" for i, c in enumerate(clauses[:5])]
    return {"one_line": "초안 요약(LLM 연결 전)", "bullets": bullets}

def risk_decision(clauses: List[str]):
    rule_hits = apply_rules(clauses)

    # 룰 히트 조항만 LLM 보냄 (없으면 상위 5개 조항)
    by_clause: Dict[int, List[Dict]] = {}
    for h in rule_hits:
        by_clause.setdefault(h["clause_id"], []).append(h)

    clause_ids = sorted(by_clause.keys()) or list(range(min(5, len(clauses))))
    candidate_texts = [clauses[i] for i in clause_ids]

    use_gemini = os.getenv("LLM_PROVIDER","gemini").lower() == "gemini" and os.getenv("GOOGLE_API_KEY")
    llm_results = gemini_batch_verdicts(candidate_texts) if use_gemini else []

    # 길이 보정
    while len(llm_results) < len(clause_ids):
        llm_results.append({"verdict":"pending","reason":"LLM 미사용/누락"})

    results = []
    for idx, cid in enumerate(clause_ids):
        llm_obj = llm_results[idx] if idx < len(llm_results) else {"verdict":"pending","reason":""}
        llm_verdict = (llm_obj.get("llm_verdict") or "pending").lower()
        llm_reason  = _normalize_ko(llm_obj.get("reason") or "")

        hits = by_clause.get(cid) or [{"type":"llm_flag","pattern":"llm_fallback"}]

        for h in hits:
            rtype = h["type"]
            base_sev = SEVERITY_BY_TYPE.get(rtype, "watch")
            desc = DESCRIPTION_BY_TYPE.get(rtype, "전세 임대차 기준의 일반적 유의사항입니다.")
            sev = base_sev if rtype != "llm_flag" else ("high" if llm_verdict=="risky" else "watch")
            reason = llm_reason if llm_reason else desc

            results.append({
                "type": rtype,
                "severity": sev,
                "rule_hits": [h.get("pattern","llm_fallback")],
                "llm_verdict": llm_verdict,              # ✅ Pydantic 허용값
                "reason": reason,
                "evidence_ids": [cid],
            })
    return _dedupe_risks(results)

def _dedupe_risks(risks: List[Dict]) -> List[Dict]:
    order = {"watch":0,"medium":1,"high":2}
    bad   = {"ok":0,"pending":1,"watch":2,"risky":3}
    merged = {}
    for r in risks:
        key = (r["type"], tuple(r["evidence_ids"]))
        if key not in merged:
            merged[key] = r
        else:
            merged[key]["rule_hits"] = list(set(merged[key]["rule_hits"] + r["rule_hits"]))
            if order.get(r["severity"],0) > order.get(merged[key]["severity"],0):
                merged[key]["severity"] = r["severity"]
            if bad.get(r["llm_verdict"],0) > bad.get(merged[key]["llm_verdict"],0):
                merged[key]["llm_verdict"] = r["llm_verdict"]
    return list(merged.values())
