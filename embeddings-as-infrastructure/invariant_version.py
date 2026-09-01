"""Invariants 3 and 4: the index must match the encoder, and the corpus.

Invariant 3, version skew. Query and document vectors must come from the same
encoder. Two encoders do not share a coordinate space, so a query embedded with
one against documents embedded with another yields cosine similarities that are
arithmetically valid and semantically meaningless.

Getting a genuinely different space here took a correction. Refitting the same
algorithm with a different random seed does NOT produce a different encoder:
truncated SVD on the same corpus converges to the same subspace regardless of
seed, so the first version of this experiment showed no damage at all. Encoder
B is now fitted on a disjoint half of the corpus, which is a real basis
difference and a fair stand-in for a model upgrade.

Invariant 4, staleness. The index is a derived artifact. A document edited
after indexing is represented by a vector describing text that no longer
exists. Retrieval succeeds, returns the document, and the content is wrong.

Both fail silently. Both are one stored field from being detectable.
"""
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from .corpus import build, build_queries

rng = np.random.default_rng(5)
DIMS = 128


def fit(train_texts, dims=DIMS, seed=0):
    vec = TfidfVectorizer(sublinear_tf=True)
    svd = TruncatedSVD(n_components=dims, random_state=seed)
    svd.fit(vec.fit_transform(train_texts))
    return vec, svd


def encode(vec, svd, texts):
    V = svd.transform(vec.transform(texts))
    return V / np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-12)


def recall(M, Q, docs, queries, k=5):
    hits = 0
    for i, (_, gold) in enumerate(queries):
        idx = np.argsort(-(M @ Q[i]))[:k]
        hits += any(docs[j]["topic"] == gold for j in idx)
    return hits / len(queries)


def main():
    docs = build()
    queries = build_queries()
    texts = [d["text"] for d in docs]
    qtexts = [q for q, _ in queries]

    vec_a, svd_a = fit(texts, seed=0)
    half = texts[::2]                       # disjoint fit: a real basis change
    vec_b, svd_b = fit(half, seed=0)

    M_a = encode(vec_a, svd_a, texts)
    Q_a = encode(vec_a, svd_a, qtexts)
    Q_b = encode(vec_b, svd_b, qtexts)

    print(f"\n{len(docs)} docs, {len(queries)} queries, {DIMS} dims.\n")
    print("Invariant 3: query encoder must match document encoder.\n")
    print(f"  matched  (docs v1, query v1):  recall@5 {recall(M_a, Q_a, docs, queries):.0%}")
    print(f"  skewed   (docs v1, query v2):  recall@5 {recall(M_a, Q_b, docs, queries):.0%}")
    print("\n  No exception is raised. Dimensions agree, dot products are finite,")
    print("  results come back ranked. They are ranked by nothing.\n")

    print("Invariant 4: the index must match the corpus.\n")
    print(f"{'stale share':>13}{'recall@5':>11}")
    print("-" * 25)
    n = len(docs)
    for share in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0):
        M = M_a.copy()
        idx = rng.choice(n, size=int(n * share), replace=False)
        if len(idx):
            M[idx] = M_a[rng.choice(n, size=len(idx))]
        print(f"{share:>12.0%}{recall(M, Q_a, docs, queries):>11.0%}")
    print()


if __name__ == "__main__":
    main()
