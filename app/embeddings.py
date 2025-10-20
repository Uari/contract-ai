# app/embeddings.py
import os
import logging
import google.generativeai as genai

EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY",""))

logger = logging.getLogger(__name__)

def embed_texts(texts: list[str]) -> list[list[float]]:
    """텍스트 리스트를 임베딩 벡터로 변환"""
    if not texts:
        return []
    
    try:
        # Gemini 임베딩: 길면 잘라서 쓰세요(문서 chunk)
        resp = genai.embed_content(model=EMBED_MODEL, content=texts)
        # google-generativeai==0.8.x는 batch 반환 형식이 아래처럼 옴
        vecs = resp["embedding"] if "embedding" in resp else resp["embeddings"]
        # vecs가 dict일 수도 있으니 안전 처리
        if isinstance(vecs, dict) and "values" in vecs:
            return [vecs["values"]]
        if isinstance(vecs, list) and vecs and isinstance(vecs[0], dict) and "values" in vecs[0]:
            return [v["values"] for v in vecs]
        return vecs
    except Exception as e:
        # 임베딩 실패 시 빈 리스트 반환
        logger.error(f"임베딩 생성 실패: {e}")
        return []
