# Testing What Will Not Sit Still

Companion code for the article. No credentials, no provider calls, about five
seconds to run.

```bash
pip install -r requirements.txt
make reproduce && make test
```

## The problem, as arithmetic

```bash
make flakiness
```

| Per-test pass rate | 10 tests | 50 | 100 | 200 | 500 |
|---|---|---|---|---|---|
| 99.9% | 99.0% | 95.1% | 90.5% | 81.9% | 60.6% |
| 99% | 90.4% | 60.5% | 36.6% | **13.4%** | 0.7% |
| 98% | 81.7% | 36.4% | 13.3% | 1.8% | 0.0% |
| 95% | 59.9% | 7.7% | 0.6% | 0.0% | 0.0% |

Non-deterministic tests do not compose. At 99% per test, six tests is enough to
make a suite red more than 5% of runs. Then someone adds a retry, then another,
then failures get triaged as "probably flaky", and within a quarter nobody
reads the output. A suite nobody reads is the same as no suite, except more
expensive and more reassuring.

Setting temperature to zero does not fix this. Greedy decoding is not
deterministic inference: floating point addition is not associative, so a
batched forward pass can produce different logits depending on batch
composition, and provider aliases move under you. You get a large variance
reduction and no guarantee.

## The fix is layering

```bash
make layers
```

```
layer             count   share  cost to run           reliability
--------------------------------------------------------------------
deterministic        15     62%  free, no model call   100%
property              5     21%  cached responses      100%
judge                 4     17%  model call per sample measured, ~85%
```

The catalogue in [`evals/coverage_split.py`](evals/coverage_split.py) is mine,
so the precise 83% is a property of the list I wrote. The defensible claim is
directional: for any feature with a structured output, the large majority of
real failure modes are deterministically checkable, and most teams have
inverted the ratio.

Including this one, which is the flagship LLM-as-judge use case:

```python
# Grounding, checked without a judge. An attendee who does not appear in
# the source text was invented, and no amount of fluent prose makes that
# acceptable. This is the check people assume needs an LLM.
invented = [a for a in attendees if a.lower() not in source_text.lower()]
```

[`booking/recorded.py`](booking/recorded.py) holds six real failure shapes,
every one of which reads as confident and correct. None survives a schema.
One of them caught a bug in my own validator: `"EST"` is present in the tz
database and is still wrong, because it is a fixed offset with no DST rules, so
a recurring appointment stored against it silently stops shifting with the
clocks. There is now a test for it.

Fixtures, not mocks. A mock encodes what you believe the model does. A
recording encodes what it did.

## The judge is an instrument nobody calibrates

```bash
make judge
```

An imperfect judge does not just add noise. It **shrinks the effect you are
trying to detect**:

```
observed_gap = true_gap * (sensitivity + specificity - 1)
```

Samples per arm to detect a regression, 80% power, 5% significance, from an 80%
baseline:

| Judge quality | J | 10 pt | 5 pt | 2 pt |
|---|---|---|---|---|
| Perfect | 1.00 | 294 | 1,094 | 6,510 |
| Excellent, 95/95 | 0.90 | 386 | 1,462 | 8,811 |
| Good, 90/90 | 0.80 | 514 | 1,977 | 12,029 |
| Typical, 85/85 | 0.70 | 702 | 2,728 | 16,722 |
| Weak, 75/75 | 0.50 | 1,471 | 5,804 | 35,943 |

Read the other way, which is how it gets used:

| Samples per arm | Perfect judge | 85/85 judge |
|---|---|---|
| 50 | 26.0% | **39.1%** |
| 100 | 17.9% | 27.4% |
| 1,000 | 5.2% | 8.3% |
| 5,000 | 2.3% | 3.7% |

**A fifty-example eval set with a decent judge cannot see a regression smaller
than about thirty-nine points.** Fifty examples is a normal eval set. Teams run
them as merge gates believing they catch five-point regressions.

One correction worth noting, because the article's first draft got it wrong.
The cost of a bad judge is often quoted as 1/J², which is a floor rather than
the answer. The shrunken gap accounts for that much; the rest comes from the
judge pulling both observed rates toward 0.5 where binomial variance is
largest. For an 85/85 judge, 1/J² predicts 2.04x and the measured cost is 2.5x.
`test_sample_size_cost_exceeds_the_one_over_j_squared_approximation` pins it.

## The four platforms

| | [promptfoo](platforms/promptfooconfig.yaml) | [Bedrock](platforms/bedrock_evaluations.py) | [Foundry](platforms/foundry_evaluation.py) | [Vertex](platforms/vertex_evaluation.py) |
|---|---|---|---|---|
| Deterministic assertions | Extensive | Limited | Via Prompt Flow | Limited |
| Judge modes | Pointwise, rubric | Pointwise | Pointwise | Pointwise, pairwise, rubric |
| Retrieval scored separately | Build it | Native | Via evaluators | Via evaluators |
| Runs in your CI | Yes | Job-based | Job-based | Job-based |
| **Calibrates your judge** | **No** | **No** | **No** | **No** |

That last row is the one to notice. All four provide the instrument. None tells
you its error bars. That work is yours regardless of which you pick, and it
determines whether any of the numbers mean anything.

Vertex's pairwise mode is underrated: judges are considerably better at "which
of these two is better" than at "score this one to five", because the
comparison cancels much of their own calibration error.

## Layout

```
booking/
  extract.py      the schema boundary. Everything past it is ordinary code.
  properties.py   invariants over recorded responses
  recorded.py     six real failure shapes, as fixtures rather than mocks
evals/
  flakiness.py    why non-deterministic tests do not compose
  judge.py        shrinkage, sample size, detectable effect
  coverage_split.py  which failures actually need a judge
platforms/        promptfoo, Bedrock, Foundry, Vertex
tests/            18 tests. Not one calls a provider.
```

## Caveats, stated once

The failure catalogue is mine and the share it implies depends on the list I
wrote. The judge sensitivity and specificity figures are illustrative inputs,
not measurements of any real judge, and the entire point is that you should
measure your own. The flakiness arithmetic assumes independent tests; real LLM
test failures correlate through the shared model, which makes whole-suite
failure lumpier without making it rarer.
