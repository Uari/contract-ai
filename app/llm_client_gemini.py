# app/llm_client_gemini.py
from __future__ import annotations

import os
import re
import json
import time
import random
from typing import List, Dict

from dotenv import load_dotenv
import google.generativeai as genai

# ========================== 환경 설정 ==========================
# .env 로드 (GOOGLE_API_KEY, GEMINI_MODEL 등)
load_dotenv()

# gRPC 비활성화: REST만 사용(로컬/서버 공통 안정화)
os.environ["GOOGLE_API_USE_GRPC"] = "false"

API_KEY = (os.getenv("GOOGLE_API_KEY") or "").strip()
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY가 설정되지 않았습니다. .env를 확인하세요.")

# 기본 모델: 무료/가성비를 고려해 flash-lite 권장
DEFAULT_MODEL = (os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite") or "").strip().strip('"').strip("'")

# Gemini API (API Key) 명시 구성
genai.configure(api_key=API_KEY)

# ========================== 유틸 함수 ==========================
def _short(name: str) -> str:
    """'models/...' 접두어 제거 + 트림."""
    return name.split("models/")[-1].strip() if name else name

def _make_model(name: str):
    """
    환경/SDK 버전에 따라 'gemini-2.5-flash' 또는 'models/gemini-2.5-flash'
    중 한 쪽만 동작하는 사례가 있어, 짧은 이름 → 풀네임 순으로 이중 시도.
    """
    short = _short(name)
    try:
        return genai.GenerativeModel(short)
    except Exception:
        return genai.GenerativeModel(f"models/{short}")

def _json_guard(s: str):
    """
    모델이 코드블럭 등 텍스트를 섞어 줄 때도 JSON만 안전 추출해 파싱.
    - ``` 블럭 내 JSON만 추출
    - 앞/뒤 잡음 제거 후 json.loads
    실패 시 None 반환
    """
    try:
        s = (s or "").strip()
        if "```" in s:
            parts = re.split(r"```+", s)
            s = next((p for p in parts if "{" in p or "[" in p), s)
        lefts = [i for i in (s.find("["), s.find("{")) if i != -1]
        if lefts:
            left = min(lefts)
            right = max(s.rfind("]"), s.rfind("}"))
            if right > left:
                s = s[left:right + 1]
        return json.loads(s)
    except Exception:
        return None

def _chunks(lst: List[str], size: int):
    """리스트를 size 단위로 분할."""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def _safe_generate(model,
                   prompt: str,
                   temperature: float = 0.2,
                   max_out: int = 256,
                   retries: int = 3,
                   base_sleep: float = 1.1) -> str:
    """
    일시적 오류/쿼터 초과(ResourceExhausted/429 등) 시 지수 백오프 + 지터로 재시도.
    마지막 실패 시 예외 전파.
    """
    for attempt in range(retries):
        try:
            resp = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_out,
                }
            )
            return (getattr(resp, "text", "") or "").strip()
        except Exception as e:
            name = e.__class__.__name__
            msg = str(e)
            transient = any(k in (name + " " + msg) for k in
                            ["ResourceExhausted", "RateLimit", "TooManyRequests", "429", "Temporarily", "Overloaded"])
            if attempt < retries - 1 and transient:
                # 지수 백오프 + 약간의 지터
                sleep = base_sleep * (1.7 ** attempt) + random.uniform(0, 0.4)
                time.sleep(sleep)
                continue
            # 마지막 시도 실패 → 예외 전파
            raise

# ========================== 메인 진입점 ==========================
def gemini_batch_verdicts(clause_texts: List[str]) -> List[Dict]:
    """
    전세 임대차 계약 조항 리스트를 받아, 각 항목별 위험 판단(JSON) 반환.
    - API Key 기반(REST)
    - 입력 강제 절단(앞/뒤 200자)
    - 출력 토큰 상한(256)
    - 배치 처리(기본 5개)
    - 지수 백오프 재시도(3회)
    """
    model = _make_model(DEFAULT_MODEL)

    # 입력 과대 방지: 앞/뒤만 캡쳐(토큰/쿼터 절약)
    trimmed: List[str] = []
    for t in clause_texts:
        t = (t or "").strip()
        if len(t) > 400:
            t = t[:200] + "\n...\n" + t[-200:]
        trimmed.append(t)

    # 배치 크기: 과도한 요청/토큰 사용을 방지
    BATCH = 5
    results: List[Dict] = []

    for batch in _chunks(trimmed, BATCH):
        schema = (
            '각 항목은 {"verdict":"risky|watch|ok|pending","reason":"한 줄 설명"} 형식. '
            "최종 출력은 JSON 배열만 포함."
        )
        items = "\n\n".join([f'{i+1}. """{t}"""' for i, t in enumerate(batch)])
        prompt = f"전세 임대차 계약 전용 위험 평가.\n{schema}\n\n대상 조항:\n{items}"

        try:
            text = _safe_generate(
                model=model,
                prompt=prompt,
                temperature=0.2,
                max_out=256,   # 출력 토큰 상한
                retries=3,     # 일시적 초과 시 재시도
                base_sleep=1.1
            )
        except Exception as e:
            # 호출 자체 실패 시, 최소한의 방어적 결과 반환
            return [{"verdict": "watch", "reason": f"Gemini 호출 실패: {type(e).__name__}"} for _ in clause_texts]

        obj = _json_guard(text)
        if isinstance(obj, list):
            results.extend(obj)
        elif isinstance(obj, dict):
            results.append(obj)
        else:
            # 파싱 실패 시 최소 watch로 채움(배치 길이만큼)
            results.extend([{"verdict": "watch", "reason": "Gemini 출력 파싱 실패"} for _ in batch])

    return results

# ========================== (선택) 로컬 핑 테스트 ==========================
if __name__ == "__main__":
    try:
        ping_model = _make_model(DEFAULT_MODEL)
        r = ping_model.generate_content("Reply with exactly one word: pong",
                                        generation_config={"max_output_tokens": 8})
        print("PING:", (getattr(r, "text", "") or "").strip())
    except Exception as e:
        print("PING FAIL:", type(e).__name__, str(e)[:300])
