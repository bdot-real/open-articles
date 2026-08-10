"""The four failure modes, as arithmetic.

No model is called. These are closed-form calculations you can check by hand,
which is the point. Change the assumptions at the top of each function to your
own traffic and see your own numbers.
"""
from dataclasses import dataclass

from finops.pricing import RATES, Usage, cost, fmt, monthly


@dataclass
class Finding:
    name: str
    naive: float          # what you would budget, monthly dollars
    actual: float         # what you will be billed, monthly dollars
    note: str

    @property
    def multiple(self) -> float:
        return self.actual / self.naive if self.naive else float("inf")


def prompt_growth(
    before_tokens: int = 200,
    after_tokens: int = 4_000,
    requests_per_day: int = 100_000,
    tier: str = "frontier",
) -> Finding:
    """A quality improvement to a system prompt is a cost change.

    It arrives through the prompt path, which has no cost review, rather than
    the infrastructure path, which does.
    """
    before = monthly(cost(tier, Usage(input_tokens=before_tokens)), requests_per_day)
    after = monthly(cost(tier, Usage(input_tokens=after_tokens)), requests_per_day)
    return Finding(
        "Prompt growth",
        before,
        after,
        f"+{after_tokens - before_tokens:,} tokens of system prompt. "
        f"Delta {fmt(after - before)}/mo. In review: a few added lines.",
    )


def quadratic_context(
    turns: int = 50,
    tokens_per_turn: int = 600,
    conversations_per_day: int = 5_000,
    tier: str = "frontier",
) -> Finding:
    """Each turn resends the accumulated history.

    Turn k sends k turns of context, so cumulative input over an n-turn
    conversation is n(n+1)/2 turn-units, not n. Reasoning linearly under-counts
    by a factor of (n+1)/2.
    """
    linear_units = turns
    actual_units = turns * (turns + 1) // 2

    per_unit = cost(tier, Usage(input_tokens=tokens_per_turn))
    naive = monthly(linear_units * per_unit, conversations_per_day)
    actual = monthly(actual_units * per_unit, conversations_per_day)
    return Finding(
        "Quadratic context",
        naive,
        actual,
        f"{turns} turns: {actual_units:,} turn-units of input, not {linear_units}. "
        f"Grows with engagement.",
    )


def retry_amplification(
    requests_per_day: int = 100_000,
    base_tokens: int = 1_500,
    expensive_share: float = 0.05,
    expensive_multiple: float = 4.0,
    timeout_rate_on_expensive: float = 0.30,
    max_retries: int = 2,
    tier: str = "frontier",
) -> Finding:
    """Retry on timeout is standard practice, and it targets your priciest calls.

    Timeouts correlate with long generations, and long generations are the
    expensive ones. So the retry policy re-runs the tail, not the average.

    Expected attempts for a call that times out with probability p, retried up
    to r times, is (1 - p^(r+1)) / (1 - p).
    """
    p = timeout_rate_on_expensive
    attempts = (1 - p ** (max_retries + 1)) / (1 - p)

    unit = cost(tier, Usage(input_tokens=base_tokens, output_tokens=base_tokens // 2))
    cheap_share = 1 - expensive_share

    naive_per_req = cheap_share * unit + expensive_share * unit * expensive_multiple
    actual_per_req = cheap_share * unit + expensive_share * unit * expensive_multiple * attempts

    return Finding(
        "Retry amplification",
        monthly(naive_per_req, requests_per_day),
        monthly(actual_per_req, requests_per_day),
        f"{attempts:.2f} attempts on the expensive {expensive_share:.0%} tail. "
        f"Smallest of the four, and it fires during an incident.",
    )


def unbounded_loop(
    tasks_per_day: int = 2_000,
    expected_iterations: int = 3,
    runaway_share: float = 0.02,
    runaway_iterations: int = 40,
    tokens_per_iteration: int = 3_000,
    tier: str = "frontier",
) -> Finding:
    """An agent with no stopping condition.

    No traffic spike and no bug in the usual sense. A small fraction of tasks
    loop, and each iteration carries the accumulated context of the last.
    """
    def loop_cost(iterations: int) -> float:
        # Context accumulates across iterations, so this is quadratic too.
        units = iterations * (iterations + 1) // 2
        return units * cost(tier, Usage(
            input_tokens=tokens_per_iteration, output_tokens=400))

    naive = monthly(loop_cost(expected_iterations), tasks_per_day)
    actual = monthly(
        (1 - runaway_share) * loop_cost(expected_iterations)
        + runaway_share * loop_cost(runaway_iterations),
        tasks_per_day,
    )
    return Finding(
        "Unbounded agent loop",
        naive,
        actual,
        f"{runaway_share:.0%} of tasks reach {runaway_iterations} iterations. "
        f"A spend cap makes this a bounded loss.",
    )


def defensive_retrieval(
    requests_per_day: int = 100_000,
    top_k_used: int = 20,
    top_k_needed: int = 5,
    tokens_per_chunk: int = 500,
    tier: str = "frontier",
) -> Finding:
    """top_k set high because recall matters and storage is cheap.

    Storage is cheap. Context is not.
    """
    needed = monthly(
        cost(tier, Usage(input_tokens=top_k_needed * tokens_per_chunk)), requests_per_day)
    used = monthly(
        cost(tier, Usage(input_tokens=top_k_used * tokens_per_chunk)), requests_per_day)
    return Finding(
        "Defensive retrieval",
        needed,
        used,
        f"top_k={top_k_used} against a real need of {top_k_needed}. "
        f"{(top_k_used - top_k_needed) * tokens_per_chunk:,} wasted tokens per request.",
    )


def caching_recovery(
    static_prompt_tokens: int = 4_000,
    requests_per_day: int = 100_000,
    tier: str = "frontier",
) -> Finding:
    """The same prompt, with the static portion behind a cache boundary.

    Prompt caching is usually sold as a discount. Its real effect is that it
    changes what you are willing to put in a system prompt.
    """
    r = RATES[tier]
    uncached = monthly(cost(tier, Usage(input_tokens=static_prompt_tokens)), requests_per_day)
    # One write per cache lifetime, reads thereafter. Assume a 5 minute TTL and
    # steady traffic, so writes are a rounding error against reads.
    cached = monthly(cost(tier, Usage(cache_read_tokens=static_prompt_tokens)), requests_per_day)
    return Finding(
        "Same prompt, cached",
        uncached,
        cached,
        f"Cache reads bill at {r.cache_read}/M against {r.input}/M fresh. "
        f"Saves {fmt(uncached - cached)}/mo. Note this row runs the other way.",
    )


ALL = [
    prompt_growth,
    quadratic_context,
    retry_amplification,
    unbounded_loop,
    defensive_retrieval,
    caching_recovery,
]
