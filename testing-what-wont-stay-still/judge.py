"""An LLM judge is a measuring instrument with unknown error rates.

Teams validate their system with a judge they never validated. That is using an
uncalibrated instrument to certify a system, and it fails in a specific,
quantifiable way that is worse than simply adding noise.

An imperfect judge does not just make your measurement noisy. It SHRINKS the
effect you are trying to detect.

    observed_rate = true_rate * sensitivity + (1 - true_rate) * (1 - specificity)

so for two systems with true pass rates p0 and p1:

    observed_gap = (p0 - p1) * (sensitivity + specificity - 1)

That multiplier is Youden's J. A judge agreeing with humans 85% of the time in
both directions has J = 0.70, so a real five point regression looks like three
and a half points.

Required sample size scales at LEAST as 1/J^2 from the shrunken gap, and in
practice somewhat worse, because an imperfect judge also pulls both observed
rates toward 0.5 where the binomial variance p(1-p) is largest. For an 85/85
judge, 1/J^2 predicts 2.04x and the true cost is about 2.5x. Quote the measured
number rather than the approximation.
"""
import math

from scipy.stats import norm


def observed_rate(true_rate: float, sens: float, spec: float) -> float:
    return true_rate * sens + (1 - true_rate) * (1 - spec)


def youden_j(sens: float, spec: float) -> float:
    return sens + spec - 1


def samples_needed(p0: float, delta: float, sens: float = 1.0, spec: float = 1.0,
                   alpha: float = 0.05, power: float = 0.80) -> int:
    """Per-arm samples to detect a regression of `delta` in pass rate.

    Two-proportion test, applied to what the judge reports rather than to the
    truth, which is the only thing you can actually observe.
    """
    o0 = observed_rate(p0, sens, spec)
    o1 = observed_rate(p0 - delta, sens, spec)
    if abs(o0 - o1) < 1e-12:
        return math.inf
    pbar = (o0 + o1) / 2
    za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)
    n = ((za * math.sqrt(2 * pbar * (1 - pbar))
          + zb * math.sqrt(o0 * (1 - o0) + o1 * (1 - o1))) ** 2) / (o0 - o1) ** 2
    return math.ceil(n)


def detectable_delta(p0: float, n: int, sens: float = 1.0, spec: float = 1.0) -> float:
    """Smallest regression detectable with n samples per arm."""
    lo, hi = 0.0005, 0.5
    for _ in range(60):
        mid = (lo + hi) / 2
        if samples_needed(p0, mid, sens, spec) <= n:
            hi = mid
        else:
            lo = mid
    return hi


def main():
    p0 = 0.80
    print(f"\nBaseline pass rate {p0:.0%}. Samples per arm to detect a regression,")
    print("at 5% significance and 80% power.\n")

    judges = [("perfect judge", 1.00, 1.00),
              ("excellent, 95/95", 0.95, 0.95),
              ("good, 90/90", 0.90, 0.90),
              ("typical, 85/85", 0.85, 0.85),
              ("weak, 75/75", 0.75, 0.75)]

    deltas = [0.10, 0.05, 0.02]
    print(f"{'judge':<20}{'J':>7}" + "".join(f"{int(d*100):>8}pt" for d in deltas))
    print("-" * (27 + 10 * len(deltas)))
    for name, se, sp in judges:
        row = "".join(f"{samples_needed(p0, d, se, sp):>10,}" for d in deltas)
        print(f"{name:<20}{youden_j(se, sp):>7.2f}{row}")

    print("\nWhat a typical eval set can actually see:\n")
    print(f"{'samples per arm':>18}{'perfect judge':>18}{'85/85 judge':>16}")
    print("-" * 52)
    for n in (50, 100, 500, 1000, 5000):
        print(f"{n:>18,}{detectable_delta(p0, n, 1.0, 1.0):>17.1%}"
              f"{detectable_delta(p0, n, 0.85, 0.85):>16.1%}")

    print("\nA 50-example eval set with a decent judge cannot see a regression")
    print("smaller than about twenty points. Most teams believe theirs catches")
    print("five, and run it as a merge gate.\n")


if __name__ == "__main__":
    main()
