"""Azure. AI Search.

The vector profile pins dimensions and metric in the index schema, and
integrated vectorization binds an embedding deployment to the index. That is
the closest any of the four gets to enforcing invariant 3, because the encoder
is part of the index definition rather than a convention on the write path.

Change the deployment and you are expected to rebuild, which is the correct
behaviour and worth knowing before you plan the migration.
"""
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration, HnswParameters, SearchField,
    SearchFieldDataType, SimpleField, VectorSearch, VectorSearchProfile)

vector_search = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(
        name="hnsw-cosine",
        parameters=HnswParameters(metric="cosine"),   # structural
    )],
    profiles=[VectorSearchProfile(
        name="default",
        algorithm_configuration_name="hnsw-cosine",
        # Binds the encoder to the index. Invariant 3, enforced.
        vectorizer_name="embed-3-20260114",
    )],
)

fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SearchField(
        name="chunk_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        vector_search_dimensions=1024,                 # structural
        vector_search_profile_name="default",
    ),
    # Semantic invariants. Still yours.
    SimpleField(name="encoder_version", type=SearchFieldDataType.String,
                filterable=True),
    SimpleField(name="corpus_revision", type=SearchFieldDataType.String,
                filterable=True),
    SimpleField(name="doc_revision", type=SearchFieldDataType.String,
                filterable=True),
]
