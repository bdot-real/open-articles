# FinOps for Tokens

Companion code for the article. Runnable, no credentials required for the demos.

Infrastructure cost used to be a provisioning decision, made at deploy time,
through a pull request, by an engineer. Token spend is a function of user input,
evaluated at runtime, with no review step anywhere in the path.

This repository contains what that change requires you to build.

## Start here

```bash
python -m simulate
```

No model is called and nothing costs anything. It prints six closed-form
calculations you can check by hand:

```
                            Budgeted        Billed    Factor
------------------------------------------------------------
Prompt growth                 $1,800       $36,000     20.0x
Quadratic context            $13,500      $344,250     25.5x
Retry amplification          $54,338       $58,023      1.1x
Unbounded agent loop          $5,400       $20,052      3.7x
Defensive retrieval          $22,500       $90,000      4.0x
Same prompt, cached          $36,000        $3,600      0.1x
```

Edit the assumptions at the top of each function in
[`simulate/failure_modes.py`](simulate/failure_modes.py) to model your own
traffic. The defaults are 100,000 requests a day at illustrative frontier-tier
pricing.

Note that retry amplification is the smallest of the four by a wide margin. It
is included because it fires during an incident, when you are least able to
absorb it, and because the honest version of this table is more useful than one
where everything is a ten-times problem.

## The missing control

A Terraform plan tells you what a change does to your bill before you merge it.
Nothing does that for a prompt change, which is how fifteen added lines carry a
five-figure monthly delta through review without comment.

```bash
python -m tools.prompt_cost_diff --base origin/main --head HEAD
```

Against a real commit that adds few-shot examples to a system prompt:

```
$ git diff --stat
 prompts/system.txt | 26 ++++++++++++++++++++++++++
 1 file changed, 26 insertions(+)

$ python -m tools.prompt_cost_diff --base HEAD~1 --head HEAD

## Prompt cost estimate

**Projected monthly change: $12,411**

> This exceeds the review threshold of $500.00 per month. Consider whether the
> static portion can sit behind a cache boundary before merging.

| File | Before | After | Delta |
|---|---:|---:|---:|
| `prompts/system.txt` | 12 | 1,391 | +1,379 |
```

Twenty-six insertions. Any reviewer approves that.

[`.github/workflows/prompt-cost.yml`](.github/workflows/prompt-cost.yml) posts
this as a PR comment and updates it in place on each push. Advisory by default.
There is a commented-out step that gates on the threshold if you want a large
delta to need a second approval.

The estimate is deliberately crude. It cannot know your new prompt will be
cached, or that it only fires on a tenth of requests. Being roughly right in
review beats being exactly right on the invoice.

## The enforcement core

```bash
make test
```

Budget enforcement has two halves, because you cannot know a request's cost
before making it:

```python
guard.reserve(ctx, tier, input_tokens)   # estimate, synchronous, before the call
text, usage = invoke(messages, ctx.as_tags())
guard.settle(ctx, tier, usage)           # actual, reconciled after
```

Three properties the tests pin down:

- **The reserve over-estimates.** An under-estimate turns the circuit breaker
  into a suggestion.
- **Unknown tenants get a default, not unlimited.** Failing open is worse than
  having no guard, because it buys you the belief that you are protected.
- **Spend is scoped by environment.** A staging load test must not exhaust the
  production budget.

`BoundedAgentLoop` caps iterations *and* spend. Iteration caps alone are not
enough, because a single iteration's cost varies by orders of magnitude
depending on accumulated context.

## The four platforms

The comparison turned up something worth stating plainly. **Two of these solve
attribution and two solve enforcement, and they are different problems.**

| | Attribution grain | Enforcement | Timing |
|---|---|---|---|
| [AWS Bedrock](platforms/bedrock.py) | Per day per usage type, or per request via invocation logs | Build it | Retrospective |
| [Azure APIM](platforms/apim-token-limit.xml) | Per request, dimensioned | Inline policy | Synchronous |
| [Google Vertex](platforms/vertex.py) | Per project via labels | Build it | Retrospective |
| [LiteLLM](platforms/litellm/) | Per request | Inline, per key | Synchronous |

Application inference profiles and Vertex labels give you a ledger. APIM's
`llm-token-limit` and LiteLLM's virtual key budgets give you a chokepoint.

Asynchronous budget alerts cannot stop runaway spend. By the time a cost anomaly
fires, the money is gone. So the architectural question is not which model or
which cloud, it is whether there is a synchronous point in the request path
where a budget can be checked and a request refused. If a dozen services call
provider SDKs directly, there is no such point, and no amount of tagging creates
one.

Try the gateway locally:

```bash
make gateway                      # LiteLLM plus Redis on :4000
make keys TENANT=acme BUDGET=200  # a virtual key with a hard cap
```

## Layout

```
finops/
  pricing.py     token counts to dollars, cache-aware. Replace the rates.
  context.py     CallContext: tenant, feature, user, trace_id
  store.py       spend counters. InMemory for tests, Redis for real.
  budget.py      reserve / settle, and BudgetExceeded
  client.py      instrumented wrapper, and BoundedAgentLoop
simulate/        the failure modes as arithmetic
tools/           prompt_cost_diff.py, the PR cost estimator
platforms/       bedrock, vertex, apim policy, litellm compose
tests/
```

## Before you use any number from this repository

The rates in `finops/pricing.py` are illustrative placeholders chosen to make
the simulator produce sensible output. They are not a rate card. Replace them
with your provider's current pricing before quoting a figure to anyone.

The same applies to `finops.yaml`. The default of 100,000 requests a day is a
round number for illustration, not your traffic.
