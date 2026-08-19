# Deploying a Prompt Is a Production Change

Companion code. No credentials, no provider calls, about five seconds.

```bash
pip install -r requirements.txt
make reproduce && make test
```

"Put prompts in version control" is the standard advice and it is not enough.
Prompt deployment has three properties code deployment does not, and the
release toolkit handles none of them.

## One: the deployable unit is a pair

```bash
make versions
```

| Week | Prompt | Alias configured | Version served | Quality | |
|---|---|---|---|---|---|
| 1 | v3 | sonnet-4-5 | ...-20250929 | 0.84 | steady |
| 3 | v3 | sonnet-4-5 | **...-20251120** | **0.71** | provider moved the alias |
| 4 | v4 | sonnet-4-5 | ...-20251120 | 0.82 | patched to compensate |
| 6 | v5 | sonnet-4-5 | ...-20251120 | 0.69 | bad deploy |

Week three is the hardest incident class here. Nobody deployed, quality fell
twelve points, and there is no changelog entry because there was no change on
your side.

Week six shows the cost. Your changelog says v3 scored 0.84, and it did,
against a model that no longer answers to that alias. On today's model v3
scores 0.71, so reverting on prompt history recovers two points. Reverting to
v4, the last release good *against the model that will actually run*, recovers
thirteen.

[`deploy/release.py`](deploy/release.py) makes the pair the unit and refuses
aliases at construction:

```python
>>> Release("extract", "prompt text", "sonnet-4-5")
UnpinnedModel: 'sonnet-4-5' looks like an alias. Pin the dated version,
or you cannot roll back to a pairing that existed.
```

Both rules are free: pin dated versions, and record the pair on every response.

## Two: your canary is statistically blind

```bash
make canary
```

At 100,000 requests/day, canarying at 5%:

| Window | Samples | Quality regression detectable (85/85 judge) | Schema-failure rise detectable |
|---|---|---|---|
| 1 hour | 208 | **18.7%** | **3.87%** |
| 6 hours | 1,250 | 7.4% | 0.78% |
| 1 day | 5,000 | 3.7% | 0.27% |
| 1 week | 35,000 | 1.4% | 0.08% |

A one-hour canary cannot see a quality regression under nineteen points.
Nineteen points is not a regression, it is a fire. But the same 208 samples see
a schema failure rise of under four points, because binomial variance collapses
near zero. **Rare-event detection is statistically cheap.**

So [`deploy/canary_gate.py`](deploy/canary_gate.py) gates on deterministic
near-zero signals and refuses to rule on anything it lacks the power to see:

```
5% schema failures   pass=False  rose 4.90%, above the 3.87% detectable at n=208
tiny rise            pass=True   warn: rose 0.05% but 208 samples can only see 3.87%
```

An earlier version of that gate multiplied the detectable floor by a tolerance,
which let a jump from 0.1% to 5% schema failures pass. There is now a test named
after it.

**Shadow, do not canary, for quality.** One hour of shadow at 100% matches a
full day of canary at 5%; six hours matches a week. Blast radius is zero
because nothing produced is served. The first draft of the article claimed
shadow simply beats canary, which is false at these settings: 5% of a day is
5,000 samples against shadow's 4,166 in an hour. Shadowing compresses the
waiting, not the sample count.

## Three: rollback does not undo what you wrote

```bash
make blast
```

```
bad_records = request_rate × time_to_detect × fraction_wrong
```

Rollback time is not in that expression.

| Detection | MTTD | Bad records | Remediation |
|---|---|---|---|
| Deterministic canary alarm | 0.1h | 20 | $8 |
| Shadow comparison, hourly | 1.0h | 249 | $100 |
| Judge-based canary at 5% | 30h | 7,500 | $3,000 |
| Customer reports it | 120h | 30,000 | $12,000 |

A factor of 1,500, and a five second revert behind a five day detection is
still a five day incident.

The architectural lever is [`deploy/two_phase.py`](deploy/two_phase.py). Same
detection time in all three rows below; the only difference is whether a wrong
output could reach durable state without a check:

| | Bad records | Remediation |
|---|---|---|
| Write directly to the store | 30,000 | $12,000 |
| Quarantine low-confidence for review | 13,499 | $5,400 |
| Two-phase: stage, verify, commit | 2,399 | $960 |

Quarantine depth is also the fastest alarm you have. It moves within seconds of
a bad deploy, needs no judge and no statistics.

## The four platforms

| | Open source | [Bedrock](platforms/bedrock_prompt_mgmt.py) | [AI Foundry](platforms/foundry_traffic_split.py) | [Vertex](platforms/vertex_traffic_split.py) |
|---|---|---|---|---|
| Prompt versioning | [Build it](deploy/release.py) | Native, ARN-addressed | Native via Prompt Flow | Build it |
| Traffic splitting | Flag service | Application layer | Endpoint-native | Endpoint-native |
| Eval tied to deployed artifact | Build it | Separate | **Same artifact** | Separate |
| Records served version | Build it | Invocation logs | Endpoint logs | Endpoint logs |
| **Enforces the pair** | **Only if you do** | **No** | **No** | **No** |

None of them stops you deploying a new prompt against a moving model
reference, which is exactly week three.

## Layout

```
deploy/
  release.py        the pair as the deployable unit. Refuses aliases.
  canary.py         power calculations for canary and shadow
  canary_gate.py    gates on what it can see, warns about what it cannot
  blast_radius.py   detection time against rollback time
  two_phase.py      stage, verify, commit. Quarantine as an alarm.
  version_matrix.py the six week scenario
platforms/          Bedrock, AI Foundry, Vertex
tests/              13 tests. No provider is called.
```

## Caveats

The six week history is constructed to make the pairing problem concrete, not
drawn from a real incident. The 6% wrong rate, the $0.40 remediation cost and
the MTTD rows are illustrative inputs, and the ratios rather than the absolute
figures are the point. Judge sensitivity and specificity are inputs you should
replace with your own measurement, per the previous article.
