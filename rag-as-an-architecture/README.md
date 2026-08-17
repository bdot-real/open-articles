# RAG as an Architecture

Companion code for the article. Two measured findings, no credentials, about
fifteen seconds to run.

```bash
pip install -r requirements.txt
make reproduce
```

Generation quality is bounded above by retrieval recall. If the right chunk was
never retrieved, your ceiling is zero, and every hour spent on prompts is spent
below a ceiling nobody measured. So this repository measures the retrieval
layer and leaves the model out entirely.

## Finding one: dense retrieval loses on identifiers

```
Corpus 766 documents. 373 queries (15 conceptual, 358 referential). Recall@5.

retriever                 conceptual         referential   overall
--------------------------------------------------------------------
Dense (LSA)               87% ± 17%          92% ±  3%       92%
BM25 (lexical)            87% ± 17%         100% ±  0%       99%
Hybrid (RRF)              87% ± 17%         100% ±  0%       99%
```

Eight points of recall on exact-identifier queries, lost by the architecture
every RAG tutorial recommends. When someone types an error code, the token that
makes the query answerable is precisely what dimensionality reduction discards.

The corpus contains 350 documents that are near-identical in form and separated
only by an identifier, which is what a real error catalogue looks like. Without
that structure any retriever finds any code and the benchmark shows nothing.
Most public RAG benchmarks are prose-only, which is why they miss this.

### Two caveats, stated before anyone else has to

**The conceptual column supports no claim.** Fifteen queries, ±17 points. It is
printed so you can see that it is uninformative rather than being left out.

**The dense arm is LSA, not a neural encoder,** because this runs offline with
no weights to download. That preserves the mechanism under test, which is that
projecting text into a reduced space blurs rare exact tokens. It understates
paraphrase understanding, where a real encoder would do better. Note the
direction: a better encoder improves the arm already winning on conceptual
queries and does nothing for identifiers, so it widens the case for hybrid.

**This benchmark was rebuilt once.** The first version had sixteen queries and
the dimensionality sweep came out non-monotonic, which is the signature of
noise. Reporting it would have been reporting nothing.

## Finding two: where the permission check happens

```bash
make perms
```

```
Broad knowledge-assistant questions only (10 queries):
  mean slots                           4.8         10.0
  returning fewer than k             100%           0%

Post-filtering silently discards 52% of the context the caller was entitled to,
on 100% of broad queries. Nothing errors. No metric moves.
```

A vector index flattens documents from many owners into one pool, so every one
is a cosine similarity away from every user. Two ways to enforce permissions:

- **Post-filter.** Rank everything, take top k, drop what the caller cannot see.
- **Pre-filter.** Restrict the candidate set, then rank within it.

Post-filtering spends its k slots before it checks anything, so slots consumed
by unauthorized documents are lost rather than backfilled.

The thing that makes this a design-review problem rather than a bug is in the
tests:

```python
def test_post_filter_also_returns_nothing_unauthorized(...):
    """Post-filtering is not insecure in the obvious way.

    That is exactly what makes it dangerous. It passes the test everyone
    writes. The problems are the two below.
    """
```

The two below are that it silently returns fewer results than requested, and
that the result count itself leaks:

```python
def test_post_filter_result_count_leaks_existence(...):
    post_narrow = [...]; post_wide = [...]
    assert post_narrow != post_wide, "counts differ, so the count is a channel"

    assert pre_narrow == pre_wide == [10] * len(BROAD), "pre-filter reveals nothing"
```

Two callers with different permissions issue an identical query. Under
post-filtering the number of results differs, and that difference is a signal
about documents the weaker caller cannot read. Under pre-filtering both get k.

```bash
make test    # 9 tests pinning every claim above
```

## The four platforms

Same task: hybrid retrieval with permission-aware filtering.

| | [Azure AI Search](platforms/azure_ai_search.py) | [Bedrock KB](platforms/bedrock_kb.py) | [Vertex AI Search](platforms/vertex_search.py) | [Postgres](platforms/postgres_hybrid.sql) |
|---|---|---|---|---|
| Hybrid | Native, RRF plus reranker | Native | Native | You write the RRF |
| Permission filter | Entra-integrated trimming | Metadata filter | Metadata filter | SQL predicate |
| Index and data consistency | Sync pipeline | Sync pipeline | Sync pipeline | Same transaction |
| Reranker | Included | Bring your own | Included | Bring your own |
| Ceiling | High | High | High | Low millions of chunks |

In every one of them the fix is a single argument in the right place:
`filter=` on Azure, `"filter"` inside `vectorSearchConfiguration` on Bedrock,
`filter=` on Vertex, and a `WHERE` clause inside both CTEs in Postgres. The
wrong version is easier to write and passes every functional test you would
think to write for it.

The Postgres file also carries the migration nobody plans for. Your index is a
derived artifact, not durable state: change the embedding model and every
vector becomes meaningless, because the new space has no relationship to the
old one. Store the model identifier alongside the vector from day one so you
can run two versions during a cutover instead of taking an outage proportional
to corpus size.

Only the `retrieval/` package runs here. The four platform files are reference
implementations needing cloud credentials.

## Layout

```
retrieval/
  corpus.py       766 docs, including 350 separated only by an identifier
  queryset.py     373 queries, powered enough for the referential claim
  retrievers.py   Dense (LSA), BM25, Hybrid (RRF)
  evaluate.py     recall@k by family, with confidence intervals
  permissions.py  pre-filter against post-filter. No model involved.
platforms/        Azure AI Search, Bedrock KB, Vertex AI Search, Postgres
tests/
```

## Caveats, stated once and clearly

The corpus is synthetic and `corpus.py` says exactly how it is built. The dense
arm is LSA and not a neural encoder. The conceptual query set is too small to
support a claim and is reported anyway so you can see that. The referential
finding and both permission findings are the parts that hold.
