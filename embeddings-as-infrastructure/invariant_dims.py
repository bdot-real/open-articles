"""Invariant 2: truncating a vector breaks its unit norm.

Matryoshka embeddings let you slice a vector to fewer dimensions and keep most
of the signal, which is a real and useful property. What people miss is that a
sliced unit vector is no longer a unit vector, and the amount of norm lost
varies per document.

So truncation silently converts a correctly built cosine index into the
unnormalised-dot situation from invariant 1, unless you renormalise after the
slice. One line, and nothing tells you when it is missing.

The dimensionality cost curve is here too, because that is the reason anyone
truncates in the first place.
"""
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from .corpus import QUERIES, build

FULL = 256


def main():
    docs = build()
    vec = TfidfVectorizer(sublinear_tf=True)
    X = vec.fit_transform([d["text"] for d in docs])
    svd = TruncatedSVD(n_components=FULL, random_state=0).fit(X)

    M = svd.transform(X)
    M = M / np.maximum(np.linalg.norm(M, axis=1, keepdims=True), 1e-12)
    Q = svd.transform(vec.transform([q for q, _ in QUERIES]))
    Q = Q / np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-12)

    def recall(Md, Qd, k=5):
        h = 0
        for i, (_, gold) in enumerate(QUERIES):
            idx = np.argsort(-(Md @ Qd[i]))[:k]
            h += any(docs[j]["topic"] == gold for j in idx)
        return h / len(QUERIES)

    print("\nInvariant 2: renormalise after truncation.\n")
    print(f"{'dims':>6}{'mean norm':>12}{'spread':>9}"
          f"{'recall, sliced':>17}{'recall, renormalised':>22}")
    print("-" * 68)
    for d in (256, 128, 64, 32, 16, 8):
        sliced_M, sliced_Q = M[:, :d], Q[:, :d]
        n = np.linalg.norm(sliced_M, axis=1)
        renorm_M = sliced_M / np.maximum(n[:, None], 1e-12)
        renorm_Q = sliced_Q / np.maximum(
            np.linalg.norm(sliced_Q, axis=1, keepdims=True), 1e-12)
        print(f"{d:>6}{n.mean():>12.3f}{n.std():>9.3f}"
              f"{recall(sliced_M, sliced_Q):>16.0%}{recall(renorm_M, renorm_Q):>21.0%}")

    print("\nThe cost curve, which is why anyone truncates. 10 million chunks:\n")
    print(f"{'dims':>6}{'float32 index':>16}{'relative':>11}")
    print("-" * 34)
    base = None
    for d in (1536, 1024, 768, 512, 256, 128):
        gb = 10_000_000 * d * 4 / 1e9
        base = base or gb
        print(f"{d:>6}{gb:>13.1f} GB{gb/base:>11.2f}x")
    print()
    print("Dimensionality is a storage, memory, index-build and query-latency")
    print("decision all at once, and it compounds with corpus size. Truncation")
    print("is the right lever. Forgetting to renormalise is the trap.\n")


if __name__ == "__main__":
    main()
