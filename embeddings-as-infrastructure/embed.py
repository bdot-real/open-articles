"""An embedding function, and the four invariants its output depends on.

TF-IDF plus truncated SVD stands in for a neural encoder so everything here
runs offline. For three of the four invariants that substitution is not an
approximation at all:

  normalization and metric   pure linear algebra, identical for any encoder
  dimensionality and cost    arithmetic on vector width
  version skew               two projections into unrelated spaces, which is
                             exactly what two encoders are

Only the absolute recall numbers are encoder-dependent. The failures are not.
"""
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer


class Encoder:
    """A versioned encoder. The version is part of its identity on purpose."""

    def __init__(self, docs, dims: int = 256, version: str = "v1", seed: int = 0):
        self.dims, self.version = dims, version
        self.vec = TfidfVectorizer(sublinear_tf=True)
        X = self.vec.fit_transform([d["text"] for d in docs])
        self.svd = TruncatedSVD(n_components=dims, random_state=seed)
        self.svd.fit(X)

    def encode(self, texts: list[str], normalize: bool = True) -> np.ndarray:
        V = self.svd.transform(self.vec.transform(texts))
        if normalize:
            n = np.linalg.norm(V, axis=1, keepdims=True)
            V = V / np.maximum(n, 1e-12)
        return V

    @property
    def fingerprint(self) -> str:
        return f"{self.version}:d{self.dims}"


def cosine(q: np.ndarray, M: np.ndarray) -> np.ndarray:
    qn = q / max(np.linalg.norm(q), 1e-12)
    Mn = M / np.maximum(np.linalg.norm(M, axis=1, keepdims=True), 1e-12)
    return Mn @ qn


def dot(q: np.ndarray, M: np.ndarray) -> np.ndarray:
    return M @ q


def recall_at_k(scores_fn, Q, M, docs, queries, k=5) -> float:
    hits = 0
    for i, (_, gold) in enumerate(queries):
        idx = np.argsort(-scores_fn(Q[i], M))[:k]
        hits += any(docs[j]["topic"] == gold for j in idx)
    return hits / len(queries)
