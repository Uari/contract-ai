# app/vector_search.py
import numpy as np
from sklearn.neighbors import NearestNeighbors

class SimpleVectorIndex:
    def __init__(self, metric: str = "cosine"):
        self.metric = metric
        self.nn = None
        self.X = None

    def build(self, embeddings: list[list[float]]):
        self.X = np.asarray(embeddings, dtype=np.float32)
        # brute + cosine → 설치/빌드 이슈 없음, 수만 건 이하 실무 충분
        self.nn = NearestNeighbors(n_neighbors=5, algorithm="brute", metric=self.metric)
        self.nn.fit(self.X)

    def query(self, qvec: list[float], k: int = 5):
        dists, idxs = self.nn.kneighbors([qvec], n_neighbors=k, return_distance=True)
        return idxs[0].tolist(), dists[0].tolist()
