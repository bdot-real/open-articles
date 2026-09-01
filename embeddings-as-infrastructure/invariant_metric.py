"""Invariant 1: the distance metric must match how the vectors were scaled.

Dot product on unnormalised vectors is not a similarity. It is a similarity
multiplied by the document's magnitude, and magnitude tracks length. The
ranking then prefers long documents regardless of relevance.

Recall@k hides this, because a long chunk of the right document still counts as
a hit. The harm shows up in WHICH chunk ranks first, which is what gets put in
the context window and what the answer is built from.

Nothing errors. The index builds, queries return, latency is fine. That is the
shape of every failure in this article.
"""
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from .corpus import QUERIES, build

VARIANTS = ("short", "medium", "long")


def build_space(docs, normalize_tfidf):
    vec = TfidfVectorizer(sublinear_tf=True,
                          norm="l2" if normalize_tfidf else None)
    X = vec.fit_transform([d["text"] for d in docs])
    svd = TruncatedSVD(n_components=256, random_state=0).fit(X)
    M = svd.transform(X)
    Q = svd.transform(vec.transform([q for q, _ in QUERIES]))
    return M, Q


def cosine(q, M):
    Mn = M / np.maximum(np.linalg.norm(M, axis=1, keepdims=True), 1e-12)
    return Mn @ (q / max(np.linalg.norm(q), 1e-12))


def dot(q, M):
    return M @ q


def variant_of(title: str) -> str | None:
    for v in VARIANTS:
        if f"({v})" in title:
            return v
    return None


def top1_variant_mix(scores_fn, Q, M, docs):
    """Of the correct-topic documents, which length variant ranks highest?

    A metric with no length bias should pick the short variant about as often
    as the long one, because all three say the same thing.
    """
    counts = dict.fromkeys(VARIANTS, 0)
    for i, (_, gold) in enumerate(QUERIES):
        order = np.argsort(-scores_fn(Q[i], M))
        for j in order:
            if docs[j]["topic"] == gold:
                counts[variant_of(docs[j]["title"])] += 1
                break
    return counts


def main():
    docs = build()

    print("\nInvariant 1: metric must match vector scaling.\n")
    for label, normalize_tfidf in (("vectors already unit norm", True),
                                   ("vectors with length-varying norm", False)):
        M, Q = build_space(docs, normalize_tfidf)
        norms = np.linalg.norm(M, axis=1)
        print(f"{label}  (norm range {norms.min():.2f} to {norms.max():.2f})")
        for name, fn in (("cosine", cosine), ("dot", dot)):
            mix = top1_variant_mix(fn, Q, M, docs)
            total = sum(mix.values())
            bar = "  ".join(f"{k} {v}/{total}" for k, v in mix.items())
            print(f"    {name:<8} top-1 variant:  {bar}")
        print()

    print("With unit-norm vectors the two metrics are identical, which is why")
    print("this bug is invisible on most modern encoders. It reappears the")
    print("moment norms vary, and the ranking then tracks length.\n")


if __name__ == "__main__":
    main()
