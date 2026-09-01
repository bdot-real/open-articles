"""Every invariant, as an executable claim.

The theme of this repository is that all four failures are silent. These tests
are the mechanism that makes them loud, so they are the most important code
here, not the experiments.
"""
import dataclasses as dc

import numpy as np
import pytest

from embeddings.corpus import build, build_queries
from embeddings.index import (EmbeddingIndex, IndexInvariantError,
                              IndexManifest, truncate)

rng = np.random.default_rng(0)


def unit(n=40, d=16):
    V = rng.normal(size=(n, d))
    return V / np.linalg.norm(V, axis=1, keepdims=True)


@pytest.fixture
def manifest():
    return IndexManifest(encoder_id="acme/embed-3", encoder_version="2026-01-14",
                         dims=16, normalized=True, metric="cosine",
                         corpus_revision="r100")


# ------------------------------------------------------- construction guards
def test_dot_on_unnormalized_vectors_is_refused(manifest):
    """Invariant 1. Ranking by magnitude is ranking by document length."""
    m = dc.replace(manifest, normalized=False, metric="dot")
    with pytest.raises(IndexInvariantError, match="magnitude"):
        EmbeddingIndex(rng.normal(size=(40, 16)) * 5, m)


def test_slicing_without_renormalizing_is_refused(manifest):
    """Invariant 2. A sliced unit vector is not a unit vector."""
    V = unit()
    with pytest.raises(IndexInvariantError, match="renormalize"):
        EmbeddingIndex(V[:, :8], dc.replace(manifest, dims=8))


def test_truncate_helper_produces_an_index_that_builds(manifest):
    V = unit()
    sliced, m2 = truncate(V, 8, manifest)
    assert m2.dims == 8
    assert np.allclose(np.linalg.norm(sliced, axis=1), 1.0)
    EmbeddingIndex(sliced, m2)


def test_manifest_dims_must_match_the_vectors(manifest):
    with pytest.raises(IndexInvariantError, match="dims"):
        EmbeddingIndex(unit(d=32), manifest)


# ----------------------------------------------------------- query-time guards
def test_encoder_version_skew_refuses_to_rank(manifest):
    """Invariant 3. Two encoders do not share a coordinate space."""
    ix = EmbeddingIndex(unit(), manifest)
    newer = dc.replace(manifest, encoder_version="2026-06-02")
    with pytest.raises(IndexInvariantError, match="encoder_version"):
        ix.search(unit(1)[0], newer)


def test_encoder_identity_skew_refuses_to_rank(manifest):
    ix = EmbeddingIndex(unit(), manifest)
    other = dc.replace(manifest, encoder_id="othercorp/embed-1")
    with pytest.raises(IndexInvariantError, match="encoder_id"):
        ix.search(unit(1)[0], other)


def test_stale_corpus_revision_refuses_to_rank(manifest):
    """Invariant 4."""
    ix = EmbeddingIndex(unit(), manifest)
    with pytest.raises(IndexInvariantError, match="corpus revision|r250"):
        ix.search(unit(1)[0], manifest, corpus_revision="r250")


def test_a_matching_manifest_searches_normally(manifest):
    V = unit()
    ix = EmbeddingIndex(V, manifest)
    hits = ix.search(V[3], manifest, k=3, corpus_revision="r100")
    assert hits[0][0] == 3
    assert hits[0][1] == pytest.approx(1.0)


def test_partial_staleness_is_visible_per_document(manifest):
    """An index-level revision cannot see partial staleness, which is the
    common case. Per-document revisions can."""
    V = unit()
    ix = EmbeddingIndex(V, manifest, doc_revisions={i: "a" for i in range(40)})
    current = {i: ("a" if i % 4 else "b") for i in range(40)}
    assert ix.stale_fraction(current) == pytest.approx(0.25)


# ------------------------------------------------------------- the measurements
def test_dot_product_ranking_tracks_document_length():
    """The headline result, asserted rather than asserted at.

    Recall stays at 100% throughout, which is why this is measured on which
    variant ranks first rather than on recall.
    """
    from embeddings.invariant_metric import (build_space, cosine, dot,
                                             top1_variant_mix)
    docs = build()
    M, Q = build_space(docs, normalize_tfidf=False)

    cos_mix = top1_variant_mix(cosine, Q, M, docs)
    dot_mix = top1_variant_mix(dot, Q, M, docs)

    assert dot_mix["long"] >= 8, "dot product should be captured by length"
    assert cos_mix["long"] <= 5, "cosine should not be"
    assert cos_mix["short"] >= 4, "cosine should still find short documents"


def test_query_set_is_powered_enough_for_the_curves():
    """An earlier version used ten queries and the staleness curve was not
    monotonic, which is noise rather than a finding."""
    assert len(build_queries()) >= 100
