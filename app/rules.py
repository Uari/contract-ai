# app/rules.py
import re
from typing import Dict, List

# -----------------------------
# 위험 패턴 정의 (정규식)
# - 키: 카테고리명
# - 값: 해당 카테고리에서 탐지할 정규식 패턴 목록
# -----------------------------
RISK_RULES: Dict[str, List[str]] = {
    # 공통(서비스/용역/IT 등)
    "liability": [
        r"모든\s*손해\s*배상",
        r"귀책(?:여부|사유)\s*무관",
        r"배상\s*한도\s*(?:없음|무제한)",
        r"간접\s*손해\s*배상",                          # indirect / consequential damages
        r"예측\s*가능\s*여부\s*무관\s*배상"
    ],
    "jurisdiction": [
        r"전속\s*관할",
        r"관할\s*법원은\s*(?:상대방|본점|주된\s*사무소|주소지)"
    ],
    "nda": [
        r"무기한\s*비밀유지",
        r"영구\s*보관",
        r"제3자\s*제공\s*무제한"
    ],
    "sla": [
        r"가동률\s*99\.\d+%.*위약금",
        r"서비스\s*중단\s*당일\s*\d+(\.\d+)?%"
    ],

    # -----------------------------
    # 임대차 전용 (주택/상가 공통으로 자주 등장하는 위험 신호)
    # -----------------------------
    "lease_deposit": [               # 보증금 관련
        r"보증금\s*미반환",
        r"보증금.*지연이자\s*\d+(\.\d+)?\s*%",
        r"보증금.*상계\s*불가",         # 임차인 상계권 박탈
        r"보증금.*압류.*책임\s*임차인"   # 과도한 책임 전가
    ],
    "lease_rent": [                  # 차임/연체
        r"차임\s*지연\s*이자\s*일\s*\d+(\.\d+)?\s*%",
        r"연체\s*이자\s*\d+(\.\d+)?\s*%",
        r"일할\s*계산\s*배제"            # 과도한 불이익
    ],
    "lease_repair": [                # 수선/수리 의무
        r"(임차인|세입자).*(수선|수리)\s*의무.*포괄",
        r"(임대인|집주인).*(수선|수리).*(면책|책임\s*없음)",
        r"하자\s*책임.*전부\s*임차인"
    ],
    "lease_termination": [           # 해지/갱신/위약
        r"중도\s*해지\s*불가",
        r"일방적\s*해지",               # 임대인 일방 해지 권한
        r"해지\s*위약금\s*\d+(\.\d+)?\s*%",
        r"묵시적\s*갱신\s*배제"
    ],
    "lease_sublease": [              # 전대/양도
        r"전대\s*금지\s*(?:.+)?사전\s*서면\s*동의.*없음",  # 완전 금지 + 동의 절차 부재
        r"권리금\s*회수\s*방해\s*면책"                   # 상가권리금 보호 무력화
    ],
    "lease_restore": [               # 원상복구
        r"원상\s*복구.*전면\s*책임",
        r"통상\s*손모.*임차인.*부담",
        r"도배|장판|설비\s*전면\s*교체\s*의무"           # 과도한 복구 범위
    ],
    "lease_penalty": [               # 위약벌/과징
        r"위약벌\s*\d+(\.\d+)?\s*%",
        r"지연\s*손해금\s*일\s*\d+(\.\d+)?\s*%",
        r"손해액\s*추정.*반증\s*배제"                    # 손해액 예정의 반증권 박탈
    ],
    "lease_utilities": [             # 관리비/공과금
        r"(관리비|공과금).*(?:일체|전부)\s*임차인\s*부담",
        r"관리비.*산정\s*근거\s*부재",                   # 기준 불명확
        r"전기|수도|가스.*누수.*임차인\s*책임"
    ],
    "lease_insurance": [             # 보험
        r"보험\s*가입\s*의무.*광범위",
        r"임대인\s*보험\s*면책.*임차인\s*부담"
    ],
    "lease_access": [                # 출입·점검
        r"임대인.*수시\s*출입",
        r"사전\s*통지\s*없이\s*출입"                     # 과도한 출입권
    ]
}

# -----------------------------
# 룰 적용 함수
# -----------------------------
def apply_rules(clauses_text: List[str]):
    """
    각 조항 텍스트에 대해 카테고리별 패턴을 매칭하여 히트 리스트 반환.
    반환 예:
    [
      {"type": "lease_deposit", "clause_id": 3, "pattern": r"..."},
      ...
    ]
    """
    hits = []
    for i, txt in enumerate(clauses_text):
        if not txt:
            continue
        # 공백 정리 후 매칭(대소문자 무시)
        norm = re.sub(r"\s+", " ", txt)
        for rtype, patterns in RISK_RULES.items():
            for pat in patterns:
                try:
                    if re.search(pat, norm, flags=re.I):
                        hits.append({"type": rtype, "clause_id": i, "pattern": pat})
                except re.error:
                    # 잘못된 정규식 패턴이 있어도 서비스 중단하지 않도록 안전 처리
                    continue
    return hits
