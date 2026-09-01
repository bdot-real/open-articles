"""Google. Vertex Vector Search.

Dimensions and distance measure are fixed at index creation, so the structural
invariants are handled. Encoder identity and corpus revision are convention,
enforced by nothing.

Restricts are the mechanism for carrying them, and they double as the
permission pre-filter from the RAG article in this series.
"""
import os

from google.cloud import aiplatform


def create_index(dims: int = 1024):
    aiplatform.init(project=os.environ["GCP_PROJECT"],
                    location=os.environ.get("GCP_LOCATION", "us-central1"))
    return aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name="chunks-embed3-20260114",   # encoder in the name, at least
        dimensions=dims,                          # structural
        approximate_neighbors_count=50,
        distance_measure_type="DOT_PRODUCT_DISTANCE",
        # Vertex expects unit-norm vectors for dot product to behave as cosine.
        # Nothing checks that. See embeddings/index.py.
    )


def datapoint(chunk_id: str, vector, encoder_version: str, corpus_revision: str,
              tenant: str):
    """Manifest fields as restricts, so a query can filter on them."""
    return {
        "datapoint_id": chunk_id,
        "feature_vector": vector,
        "restricts": [
            {"namespace": "encoder_version", "allow_list": [encoder_version]},
            {"namespace": "corpus_revision", "allow_list": [corpus_revision]},
            {"namespace": "tenant", "allow_list": [tenant, "shared"]},
        ],
    }
