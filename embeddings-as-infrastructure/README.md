# Embeddings as Infrastructure

Companion code. No credentials, no downloads, about ten seconds.

```bash
pip install -r requirements.txt
make reproduce && make test
```

A vector index is the only artifact in your system that degrades into plausible
output instead of an error. An embedding is 128 floats whose meaning is set
entirely by an encoder that is not present, at a version that is not recorded,
under a normalization convention that is not stated, describing text that may
have changed since.

Four invariants, all measured, all silent when broken.

## 1. The metric must match the scaling

```bash
make metric
```

Each query has three variants of the correct document: same content, different
lengths. An unbiased metric picks them at roughly equal rates.

```
vectors with length-varying norm  (norm range 4.93 to 71.12)
    cosine   top-1 variant:  short 5/10  medium 1/10  long 4/10
    dot      top-1 variant:  short 1/10  medium 0/10  long 9/10
```

Nine of ten top results chosen by word count. **Recall@5 was 100% in both
cases**, because a long chunk of the right document still counts as a hit. The
standard retrieval metric cannot see this at all.

Even norms between 0.81 and 1.00, which most people would call normalized,
moved nine of ten results. That is why the bug is invisible on encoders that
emit near-unit vectors, and why it returns the moment anything perturbs them.

## 2. Truncating breaks unit norm

```bash
make dims
```

| Dimensions | Mean norm | Spread | Recall, sliced | Recall, renormalized |
|---|---|---|---|---|
| 128 | 0.918 | 0.097 | 100% | 100% |
| 32 | 0.839 | 0.152 | 100% | 100% |
| 8 | 0.766 | 0.247 | **10%** | **80%** |

Matryoshka slicing is a real lever: 10M chunks at 1536 dims is 61 GB, at 128
dims it is 5 GB. But a sliced unit vector is not a unit vector, and one line
of renormalization is worth 8x at aggressive truncation.

Read the middle rows carefully. Recall does not move while norm spread grows
steadily, and per invariant 1, spread is what drives the length bias recall
cannot see. Recall stops being a useful instrument well before it starts
moving.

## 3. The query encoder must match the document encoder

```bash
make version
```

| | Recall@5 |
|---|---|
| Docs v1, query v1 | 100% |
| Docs v1, query v2 | **20%** |

Dimensions agree, dot products are finite, results come back ranked. They are
ranked by nothing.

This one needed a correction and the correction is instructive. The first
version built encoder two by refitting with a different random seed and
measured zero damage, because truncated SVD on the same corpus converges to
the same subspace regardless of seed. That was the same encoder twice, not two
encoders. Encoder two is now fitted on a disjoint half of the corpus.

## 4. The index must match the corpus

| Stale share | Recall@5 |
|---|---|
| 10% | 100% |
| 25% | 90% |
| 50% | 80% |
| 75% | 36% |

Gentle, then not. Ten percent stale costs nothing measurable, which is exactly
how an index reaches fifty percent: no single day's drift is visible.

These curves use 120 generated queries. The first version used ten hand-written
ones and the staleness curve went down, up, then down again, which is the
signature of an underpowered measurement rather than a finding.

## The fix: six fields and four assertions

[`embeddings/index.py`](embeddings/index.py) refuses to answer when its
invariants are violated:

```
encoder_version mismatch: index has '2026-01-14', query has '2026-06-02'.
Refusing to rank, because the result would be meaningless rather than
wrong in a visible way.

manifest claims normalized vectors, largest deviation is 0.758.
Truncating a unit vector does not preserve unit norm; renormalize after slicing.

dot product on unnormalized vectors ranks by magnitude, which tracks
document length. Use cosine, or normalize first.
```

That refusal is the entire point. The default behaviour of every failure above
is to answer confidently.

```bash
make test    # 11 tests, one per invariant plus the measurements
```

## The four platforms

| | Dimensions | Metric | Encoder version | Corpus revision |
|---|---|---|---|---|
| [Bedrock KB](platforms/bedrock_opensearch.py) | Index mapping | Index mapping | Your metadata | Your metadata |
| [Azure AI Search](platforms/azure_ai_search.py) | Index schema | Index schema | **Bound deployment** | Your field |
| [Vertex](platforms/vertex_vector_search.py) | Creation time | Creation time | Convention | Convention |
| [pgvector](platforms/pgvector_manifest.sql) | Column type | **Per query** | Your column | Your column |

The pattern: dimensions and metric are structural, so every platform enforces
them. Encoder version and corpus revision are semantic, so none does. Those two
produced the 20% and the 30% above.

pgvector is the outlier in both directions. The metric lives in the operator
you write (`<=>` cosine, `<#>` inner product), so it can differ per call site,
which is the exact hazard of invariant 1. It is also the only one where the
manifest can be a real table with a foreign key and a CHECK constraint,
verified in the same transaction as the write:

```sql
CONSTRAINT dot_requires_normalized
    CHECK (metric <> 'dot' OR normalized)
```

## Layout

```
embeddings/
  corpus.py             530 docs with deliberately varied lengths, 120 queries
  embed.py              the encoder, and why LSA is a fair stand-in here
  index.py              the manifest, and an index that refuses on mismatch
  invariant_metric.py   1: metric against scaling
  invariant_dims.py     2: truncation, and the cost curve
  invariant_version.py  3 and 4: encoder skew, staleness
platforms/              Bedrock KB, Azure AI Search, Vertex, pgvector
tests/                  11 tests
```

## Caveats

The encoder is TF-IDF plus truncated SVD so this runs offline. For three of the
four invariants that is not an approximation: normalization and metric
interaction is linear algebra, the cost curve is arithmetic on vector width,
and two separately fitted bases genuinely do not share a coordinate space.
Only the absolute recall figures are encoder-dependent; the failures are not.
The corpus is synthetic and `corpus.py` states how it is built.
