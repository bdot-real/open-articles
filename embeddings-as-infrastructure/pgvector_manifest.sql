-- Open source. pgvector.
--
-- The column type fixes dimensionality. The METRIC does not live in the
-- schema: it is the operator you write in the query, so it can differ per call
-- site. That is a genuine hazard, and invariant 1 is exactly the bug it
-- produces.
--
--   <=>  cosine distance
--   <#>  negative inner product      <- ranks by magnitude on non-unit vectors
--   <->  L2 distance
--
-- It is also a genuine advantage no managed service offers: the manifest can
-- be a real table with a foreign key, checked in the same transaction as the
-- write. Correctness by construction rather than by convention.

CREATE TABLE index_manifest (
    id              bigserial PRIMARY KEY,
    encoder_id      text    NOT NULL,
    encoder_version text    NOT NULL,          -- dated, never an alias
    dims            int     NOT NULL,
    normalized      boolean NOT NULL,
    metric          text    NOT NULL CHECK (metric IN ('cosine', 'dot', 'l2')),
    corpus_revision text    NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),

    -- Invariant 1, enforced by the database rather than by a code review.
    CONSTRAINT dot_requires_normalized
        CHECK (metric <> 'dot' OR normalized)
);

CREATE TABLE chunks (
    id           bigserial PRIMARY KEY,
    document_id  bigint NOT NULL,
    manifest_id  bigint NOT NULL REFERENCES index_manifest(id),
    doc_revision text   NOT NULL,              -- catches partial staleness
    content      text   NOT NULL,
    embedding    vector(1024) NOT NULL,
    tenant       text   NOT NULL
);

CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON chunks (manifest_id);

-- Query: constrain to one manifest, so a partially re-indexed table cannot
-- silently mix two coordinate spaces in one result set. This is the failure
-- that measured 20% recall.
SELECT c.id, c.content, 1 - (c.embedding <=> %(vec)s) AS similarity
FROM chunks c
WHERE c.manifest_id = %(manifest_id)s
  AND (c.tenant = %(tenant)s OR c.tenant = 'shared')
ORDER BY c.embedding <=> %(vec)s
LIMIT %(k)s;

-- Staleness, as a query rather than a hope.
SELECT m.encoder_version,
       count(*) FILTER (WHERE c.doc_revision <> d.revision) AS stale,
       count(*)                                             AS total,
       round(100.0 * count(*) FILTER (WHERE c.doc_revision <> d.revision)
             / count(*), 1) AS stale_pct
FROM chunks c
JOIN documents d ON d.id = c.document_id
JOIN index_manifest m ON m.id = c.manifest_id
GROUP BY m.encoder_version;
