"""AWS. Bedrock Knowledge Bases over OpenSearch Serverless.

Dimensions and similarity method are declared in the index mapping, so the
metric is structural rather than a query-time choice. That is invariant 1
enforced for you.

Encoder version and corpus revision are metadata fields you add, and nothing
requires you to. Those are the two that produced the 20% and 30% recall in the
experiments, so add them.
"""
MAPPING = {
    "settings": {"index": {"knn": True}},
    "mappings": {"properties": {
        "chunk_vector": {
            "type": "knn_vector",
            "dimension": 1024,
            # Structural. The metric cannot drift per call site.
            "method": {"name": "hnsw", "engine": "faiss",
                       "space_type": "cosinesimil"},
        },
        # Not required by anyone. Add them anyway.
        "encoder_id":      {"type": "keyword"},
        "encoder_version": {"type": "keyword"},   # dated, never an alias
        "corpus_revision": {"type": "keyword"},
        "doc_revision":    {"type": "keyword"},   # catches partial staleness
        "tenant":          {"type": "keyword"},
    }},
}


def query(vector, encoder_version: str, corpus_revision: str, k: int = 5):
    """Filter on the manifest fields rather than trusting them.

    A vector written by a different encoder version is not merely lower
    quality, it is meaningless. Excluding it is more correct than ranking it.
    """
    return {
        "size": k,
        "query": {"bool": {
            "filter": [
                {"term": {"encoder_version": encoder_version}},
                {"term": {"corpus_revision": corpus_revision}},
            ],
            "must": [{"knn": {"chunk_vector": {"vector": vector, "k": k}}}],
        }},
    }
