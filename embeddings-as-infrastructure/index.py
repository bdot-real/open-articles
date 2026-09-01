"""An index that refuses to answer when its invariants are violated.

Every failure in this article is silent. None raises, none logs, none moves a
latency or error metric. The index builds, the query returns, the numbers are
finite, and retrieval is quietly worse or completely meaningless.

The fix is not clever. It is four fields stored next to the vectors and four
assertions at query time. Together they turn every silent failure above into a
loud one, which is the only property that matters.
"""
from dataclasses import dataclass

import numpy as np


class IndexInvariantError(RuntimeError):
    """Raised instead of returning confidently ranked nonsense."""


@dataclass(frozen=True)
class IndexManifest:
    """What the vectors are, written down next to the vectors.

    Cheap to store, impossible to reconstruct later. The manifest is the entire
    difference between an incident you can diagnose and one you cannot.
    """
    encoder_id: str          # provider and model, e.g. "acme/embed-3"
    encoder_version: str     # dated, never an alias. Same rule as prompts.
    dims: int
    normalized: bool
    metric: str              # "cosine" or "dot"
    corpus_revision: str     # bumps whenever a document changes

    def assert_compatible(self, other: "IndexManifest") -> None:
        for field in ("encoder_id", "encoder_version", "dims", "normalized", "metric"):
            mine, theirs = getattr(self, field), getattr(other, field)
            if mine != theirs:
                raise IndexInvariantError(
                    f"{field} mismatch: index has {mine!r}, query has {theirs!r}. "
                    f"Refusing to rank, because the result would be meaningless "
                    f"rather than wrong in a visible way."
                )


class EmbeddingIndex:
    def __init__(self, vectors: np.ndarray, manifest: IndexManifest,
                 doc_revisions: dict[int, str] | None = None):
        if manifest.dims != vectors.shape[1]:
            raise IndexInvariantError(
                f"manifest says {manifest.dims} dims, vectors have {vectors.shape[1]}")

        if manifest.normalized:
            norms = np.linalg.norm(vectors, axis=1)
            drift = float(np.abs(norms - 1.0).max())
            if drift > 1e-3:
                raise IndexInvariantError(
                    f"manifest claims normalized vectors, largest deviation is "
                    f"{drift:.3f}. Truncating a unit vector does not preserve "
                    f"unit norm; renormalize after slicing."
                )
        if manifest.metric == "dot" and not manifest.normalized:
            raise IndexInvariantError(
                "dot product on unnormalized vectors ranks by magnitude, which "
                "tracks document length. Use cosine, or normalize first."
            )

        self.vectors = vectors
        self.manifest = manifest
        self.doc_revisions = doc_revisions or {}

    def search(self, query_vec: np.ndarray, query_manifest: IndexManifest,
               k: int = 5, corpus_revision: str | None = None):
        self.manifest.assert_compatible(query_manifest)

        if corpus_revision is not None and corpus_revision != self.manifest.corpus_revision:
            raise IndexInvariantError(
                f"index built at corpus revision "
                f"{self.manifest.corpus_revision!r}, corpus is now "
                f"{corpus_revision!r}. Vectors describe text that has changed."
            )

        scores = self.vectors @ query_vec
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top]

    def stale_fraction(self, current: dict[int, str]) -> float:
        """Per-document revisions catch partial staleness the manifest cannot."""
        if not self.doc_revisions:
            return 0.0
        stale = sum(1 for i, rev in self.doc_revisions.items()
                    if current.get(i) != rev)
        return stale / len(self.doc_revisions)


def truncate(vectors: np.ndarray, dims: int, manifest: IndexManifest):
    """Matryoshka truncation, done correctly.

    The renormalize line is the whole function. Omitting it is the bug in
    invariant 2, and nothing in any vector database will tell you.
    """
    sliced = vectors[:, :dims]
    sliced = sliced / np.maximum(np.linalg.norm(sliced, axis=1, keepdims=True), 1e-12)
    from dataclasses import replace
    return sliced, replace(manifest, dims=dims)
