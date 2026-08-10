"""Token counts to dollars.

Prices move. They live in one file so that when they move you change one file.
The figures below are illustrative placeholders chosen to make the simulator
produce sensible output. Replace them with your provider's current rate card
before you quote any number from this repository to anyone.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Rate:
    """Dollars per million tokens."""
    input: float
    output: float
    cache_write: float = 0.0
    cache_read: float = 0.0

    @property
    def has_caching(self) -> bool:
        return self.cache_read > 0


# Illustrative tiers, not a rate card. Verify before use.
RATES = {
    "frontier": Rate(input=3.00, output=15.00, cache_write=3.75, cache_read=0.30),
    "mid":      Rate(input=0.80, output=4.00,  cache_write=1.00, cache_read=0.08),
    "small":    Rate(input=0.15, output=0.60,  cache_write=0.19, cache_read=0.015),
}


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0


def cost(tier: str, usage: Usage) -> float:
    """Dollars for one call.

    Cached input is billed separately and far more cheaply than fresh input,
    which is why moving static context behind a cache boundary changes the
    order of magnitude rather than trimming a percentage.
    """
    r = RATES[tier]
    return (
        usage.input_tokens        * r.input       / 1_000_000
        + usage.output_tokens     * r.output      / 1_000_000
        + usage.cache_write_tokens * r.cache_write / 1_000_000
        + usage.cache_read_tokens  * r.cache_read  / 1_000_000
    )


def monthly(per_request: float, requests_per_day: int, days: int = 30) -> float:
    return per_request * requests_per_day * days


def fmt(dollars: float) -> str:
    if abs(dollars) >= 1000:
        return f"${dollars:,.0f}"
    if abs(dollars) >= 1:
        return f"${dollars:,.2f}"
    return f"${dollars:.5f}"
