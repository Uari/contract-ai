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

def _clean_quotes_commas(s: str) -> str:
    # 라인 앞뒤의 따옴표/쉼표 제거
    s = s.strip()
    s = s.strip('",“”‘’')
    return s


def split_into_clauses(pages: List[str]) -> List[str]:
    text = "\n".join(pages or [])
    if not text.strip():
        return []

    # 1) 정식 헤더로 먼저 시도
    matches = list(PAT_HEADER.finditer(text))
    chunks: List[str] = []

    if matches:
        starts = [m.start() for m in matches] + [len(text)]
        for i in range(len(starts) - 1):
            chunk = text[starts[i]:starts[i+1]].strip()
            chunk = "\n".join(_clean_quotes_commas(l) for l in chunk.splitlines())
            if len(chunk) > 20:
                chunks.append(chunk)
        return chunks

    # 2) 실패 시: '숫자.' 패턴 기준으로 줄단위 분할 (줄 시작이 아니어도 허용)
    rough = re.split(r"\n(?=\s*\"?\s*\d+\.)", text)  # 예:  \n 1.  / \n "1.
    for r in rough:
        r = r.strip()
        if not r:
            continue
        lines = [ _clean_quotes_commas(x) for x in r.splitlines() ]
        cleaned = " ".join(l for l in lines if l)
        if len(cleaned) > 20:
            chunks.append(cleaned)
    return chunks
