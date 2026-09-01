# Agents Are Distributed Systems With a Non-Deterministic Orchestrator

Companion code. No credentials, no provider calls, about fifteen seconds.

```bash
pip install -r requirements.txt
make reproduce && make test
```

A tool call is an RPC. The agent is the client, the tool is the service, and
the channel fails in all the usual ways. We spent twenty years writing down how
to handle that, then made the client a language model and shipped a `for` loop
with a try/except.

**The simulations are models, not measurements.** Parameters live at the top of
each file and are assumptions. The value is in the structure and the
sensitivity, not the absolute numbers. The executor and its tests are not
simulations; they are the part to actually use.

## Retries do not work the way you expect

```bash
make reliability
```

Distributed systems retry logic assumes transient failure: a blip, a timeout,
an overloaded service. Agent failures are substantially **persistent**, meaning
the cause is in the context, so retrying with the same context reproduces it.

Ten step task, 60% of failures context-caused:

| Retries | Blind retry | Replan | Gap |
|---|---|---|---|
| 1 | 82.8% | 94.0% | +11.1% |
| 2 | 83.1% | 98.3% | +15.2% |
| 5 | 83.5% | 99.9% | +16.5% |

**Blind retry saturates at 83%.** Going from one retry to five buys 0.7 points,
because everything left will fail every time. You are paying for four more
model calls to re-run a computation whose inputs have not changed.

The gap survives the assumption, which is the only reason to trust a
simulation:

| Failures caused by context | Blind | Replan | Gap |
|---|---|---|---|
| 20% | 94.3% | 99.4% | +5.1% |
| 60% | 83.9% | 98.2% | +14.3% |
| 95% | 75.0% | 97.2% | +22.2% |

## A timeout is not a failure

```bash
make effects
```

It is an unknown outcome. The request may have arrived, been processed and
committed, with only the response lost.

| | Duplicate operations per day |
|---|---|
| Single tool call | 2,273 |
| Ten step agent | **22,733** |

At 100,000 tasks a day, 4% timeouts, 55% of those already committed. Bookings,
charges, emails. With idempotency keys it is zero.

None of it appears in a success metric. The task completed. The agent reported
success and was right: the booking exists. It exists twice.

## The executor

[`agent/executor.py`](agent/executor.py) is the part to use. It turns on one
field no agent framework asks you for:

```python
class Effect(Enum):
    READ = "read"              # safe to repeat freely
    IDEMPOTENT = "idempotent"  # safe to repeat WITH a key
    MUTATING = "mutating"      # never repeat without confirming outcome
```

With it, a timeout on a mutation becomes a refusal:

```
book timed out and is MUTATING. Outcome is unknown; confirm before
any retry. Key: 4f2a...
```

and a persistent failure stops burning money:

```
validate failed persistently and no replan was supplied. Retrying the
same context reproduces it.
```

Two details worth stealing:

**Keys are derived from the arguments**, not a request id. A replan that
changes the operation correctly gets a new key; a blind retry of the same
operation correctly reuses the old one. Hand-rolled versions usually hash a
request id and get this backwards.

**Budgets are two numbers.** A step cap does not bound spend, because a step's
cost varies by orders of magnitude with accumulated context.

```bash
make test    # 13 tests on the safeguards
```

## The four platforms

| | Effect declared | Idempotency | Replan hook | Budget |
|---|---|---|---|---|
| [Bedrock AgentCore](platforms/bedrock_agentcore.py) | No | Your handler | Your orchestration | Session limits |
| [AI Foundry](platforms/foundry_openapi.py) | **Via HTTP method** | `Idempotency-Key` | Your orchestration | Your code |
| [Gemini Agent Platform](platforms/vertex_function_calling.py) | No | Your handler | Your orchestration | Your code |
| [MCP](platforms/mcp_annotations.py) | **Hints in the spec** | Your server | Your client | Your client |

Two are worth singling out.

**MCP** carries `readOnlyHint`, `destructiveHint` and `idempotentHint` in tool
annotations. That is the closest the `Effect` enum gets to existing as a
standard, and a real argument for MCP with nothing to do with interoperability.
They are hints, so `effect_from_annotations` defaults to `MUTATING` when they
are absent: the cost of wrongly assuming a tool is safe to repeat is unbounded,
and the cost of the opposite is one extra confirmation.

**AI Foundry with OpenAPI tools** gets the classification for free, because
HTTP already encodes it. GET is a read, PUT is idempotent, POST is not. Tools
that POST for everything come back classified `MUTATING`, which is both the
safe default and a useful smell.

The Vertex file refuses rather than guesses:

```python
raise KeyError(
    f"{function_name!r} has no effect classification. Add it to EFFECTS "
    f"before registering the tool: retry behaviour cannot be decided "
    f"without it.")
```

There is no good default. MUTATING is safe but disables retries on reads. READ
is fast and double-books people. So require the decision.

## Layout

```
agent/
  executor.py       effect classes, keyed retries, replan, budgets, trace
  reliability.py    blind retry against replan, with a sensitivity sweep
  side_effects.py   duplicate operations from retried timeouts
platforms/          Bedrock AgentCore, AI Foundry, MCP, Vertex
tests/              13 tests on the safeguards
```

## Caveats

`reliability.py` and `side_effects.py` are simulations with assumed parameters
and no claim to describe any real agent. Per-step success rates, the share of
failures caused by context, timeout rates and commit-on-timeout rates are all
inputs. Substitute your own. What the sensitivity sweep supports is that the
recommendation holds across the plausible range, which is the strongest thing a
model of this kind can say.
