# 임베딩 & FAISS

from sentence_transformers import SentenceTransformer
import numpy as np, faiss, os

class EmbedIndex:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.emb = None

    def fit(self, texts):
        vecs = self.model.encode(texts, normalize_embeddings=True)
        self.emb = np.array(vecs, dtype="float32")
        self.index = faiss.IndexFlatIP(self.emb.shape[1])
        self.index.add(self.emb)

    def search(self, query: str, k: int = 3):
        q = self.model.encode([query], normalize_embeddings=True).astype("float32")
        sims, ids = self.index.search(q, k)
        return ids[0].tolist(), sims[0].tolist()
