# Code Review When Half the Diff Was Machine-Written

Companion code for the article. Runnable, not illustrative.

Two things live here:

1. **A conformance suite** that catches four subtle spec violations in an
   implementation that looks completely fine.
2. **A spec-anchored review pass** implemented four ways, on AWS Bedrock,
   Azure AI Foundry, Google's Gemini Enterprise Agent Platform, and any
   self-hosted OpenAI-compatible server.

## The demo

Read [`conformance/plausible.py`](conformance/plausible.py) first. It is well
formatted, fully type-hinted, and documented. Every function looks right.

Count how many bugs you find by eye. Then:

```bash
pip install pytest
make demo
```

Five tests fail, covering four spec rules:

| Rule | What the plausible implementation did |
|---|---|
| 1. Half-open intervals | Used `<=`, so back-to-back bookings collide |
| 2. UTC storage | (passes) |
| 3. DST-aware recurrence | Added 24h of elapsed time instead of one calendar day |
| 4. Month-end recurrence | Clamped the 31st to the 28th instead of skipping February |

Two characters caused the first one. Reading found it in two hours. The suite
finds it in fifty milliseconds, every time, forever.

```bash
make test    # the same suite against conformance/reference.py, passes 10/10
```

## Why the tests belong to the project

If a contributor generates the implementation and the tests together, the tests
encode what the code *does*, not what the spec *requires*. A generated test for
the buggy conflict check would have asserted `has_conflict(a, b) is True`, and
passed, and CI would have been green, and the system would have been wrong.

Contributors bring implementations. The project brings truth.

## The review pass

Not "review this code", which produces confident noise about naming. Instead:
given these five numbered rules, report violations of these rules only.

```bash
cp .env.example .env          # pick a backend
make review-dry               # assemble the prompt, call nothing, cost nothing

python -m review.cli --base origin/main --head HEAD --backend local
```

One environment variable swaps the provider:

```bash
REVIEW_BACKEND=bedrock   # review/backends/bedrock.py
REVIEW_BACKEND=foundry   # review/backends/foundry.py
REVIEW_BACKEND=gemini    # review/backends/gemini.py
REVIEW_BACKEND=local     # review/backends/openai_compat.py
```

The pipeline around it does not change, which is the point. The model is the
least interesting part of this repository.

The pass is **advisory and always exits 0**. Gating a merge on a
non-deterministic reviewer teaches contributors to rewrite correct code to
appease a machine. The conformance suite is the gate.

## Workflows

| File | Does |
|---|---|
| `.github/workflows/conformance.yml` | Runs the suite. This is the merge gate. |
| `.github/workflows/review-budget.yml` | Rejects PRs over 400 lines or 15 files, excluding lockfiles and vendored paths. |
| `.github/workflows/spec-review.yml` | Posts the spec-anchored review as a PR comment. |
| `.github/pull_request_template.md` | Asks for provenance. The third question is the filter. |

## Layout

```
conformance/
  models.py            Appointment, UTC-only by construction
  reference.py         conforming implementation
  plausible.py         machine-written, four rules violated, looks fine
  test_conformance.py  the suite. OSSS_IMPL selects the target.
review/
  prompt.py            SPEC_RULES and the review prompt
  cli.py               entry point
  backends/            bedrock, foundry, gemini, openai_compat
```

## Adapting this to your project

Replace `SPEC_RULES` in `review/prompt.py` with your own numbered rules, and
replace `conformance/` with your own executable spec. Keep the rules short.
Every rule you add dilutes the others.

The scheduling specifics here are incidental. What transfers is the shape: an
executable spec as the gate, a bounded diff, and an advisory model pass that
knows what it is looking for.
