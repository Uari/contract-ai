import re
from typing import List

# 한국어 계약서 헤더 패턴 (비캡처 그룹으로 구성)
PAT_HEADER = re.compile(
    r"""
    ^\s*(?:제?\s*\d+(?:\.\d+)*\s*조[^\n]*$)   |   # '제1조 목적', '제2조(임대차기간)' 등
    ^\s*(?:\d+\.\s+[^\n]+)$                   |   # '1. 정의' 같은 숫자-점 헤더
    ^\s*(?:\[[^\]]+\])\s*$                        # '[정의]' 스타일
    """,
    re.M | re.X
)

def split_into_clauses(pages: List[str]) -> List[str]:
    """
    페이지 텍스트를 하나로 합친 뒤 헤더 매칭 위치로 슬라이스.
    캡처 그룹을 쓰지 않아 None이 끼어들지 않음.
    """
    text = "\n".join(pages or [])
    if not text.strip():
        return []

    matches = list(PAT_HEADER.finditer(text))
    if not matches:
        # 헤더가 전혀 없으면 문단 기준으로 적당히 분할
        chunks = [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) > 20]
        return chunks

    # 헤더 시작 위치들 + 문서 끝
    starts = [m.start() for m in matches]
    starts.append(len(text))

    chunks: List[str] = []
    for i in range(len(starts) - 1):
        chunk = text[starts[i]:starts[i+1]].strip()
        if len(chunk) > 20:
            chunks.append(chunk)

    return chunks
