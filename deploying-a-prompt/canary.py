"""Can a canary see the regression it is supposed to catch?

A canary is a statistical test with a sample size set by traffic, canary share
and patience. Nobody writes it down as a power calculation, so nobody notices
when the answer is no.
"""
import math

from scipy.stats import norm


def samples(rps_per_day: int, share: float, hours: float) -> int:
    return int(rps_per_day * share * hours / 24)


def detectable(p0: float, n: int, sens: float = 1.0, spec: float = 1.0,
               alpha: float = 0.05, power: float = 0.80) -> float:
    """Smallest detectable change in a proportion, given n per arm."""
    def needed(delta):
        o0 = p0 * sens + (1 - p0) * (1 - spec)
        o1 = (p0 - delta) * sens + (1 - (p0 - delta)) * (1 - spec)
        if abs(o0 - o1) < 1e-15:
            return math.inf
        pbar = (o0 + o1) / 2
        za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)
        return ((za * math.sqrt(2 * pbar * (1 - pbar))
                 + zb * math.sqrt(o0 * (1 - o0) + o1 * (1 - o1))) ** 2) / (o0 - o1) ** 2
    lo, hi = 1e-5, min(p0, 1 - p0, 0.5)
    for _ in range(80):
        mid = (lo + hi) / 2
        if needed(mid) <= n:
            hi = mid
        else:
            lo = mid
    return hi


def rise_detectable(p0: float, n: int, alpha=0.05, power=0.80) -> float:
    """Smallest detectable RISE from a near-zero baseline.

    Rare-event detection is statistically cheap, because binomial variance
    p(1-p) is tiny near zero. This is the whole constructive answer.
    """
    def needed(delta):
        o0, o1 = p0, p0 + delta
        pbar = (o0 + o1) / 2
        za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)
        return ((za * math.sqrt(2 * pbar * (1 - pbar))
                 + zb * math.sqrt(o0 * (1 - o0) + o1 * (1 - o1))) ** 2) / (o1 - o0) ** 2
    lo, hi = 1e-6, 0.5
    for _ in range(80):
        mid = (lo + hi) / 2
        if needed(mid) <= n:
            hi = mid
        else:
            lo = mid
    return hi


def main():
    daily = 100_000
    print(f"\nTraffic {daily:,} requests/day. Canary at 5%.\n")
    print(f"{'window':>10}{'samples':>10}{'quality, 85/85 judge':>24}"
          f"{'schema failures':>19}")
    print("-" * 63)
    for label, hours in [("1 hour", 1), ("6 hours", 6), ("1 day", 24),
                         ("3 days", 72), ("1 week", 168)]:
        n = samples(daily, 0.05, hours)
        q = detectable(0.80, n, 0.85, 0.85)
        s = rise_detectable(0.001, n)
        print(f"{label:>10}{n:>10,}{q:>23.1%}{s:>19.2%}")

    print("\nSame traffic, shadowed at 100% instead of canaried at 5%:\n")
    print(f"{'window':>10}{'samples':>10}{'quality, 85/85 judge':>24}")
    print("-" * 44)
    for label, hours in [("1 hour", 1), ("6 hours", 6), ("1 day", 24)]:
        n = samples(daily, 1.0, hours)
        print(f"{label:>10}{n:>10,}{detectable(0.80, n, 0.85, 0.85):>23.1%}")
    print()


if __name__ == "__main__":
    main()
