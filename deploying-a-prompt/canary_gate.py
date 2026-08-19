"""A canary gate that only judges what it can see.

Two classes of signal, and the difference is statistical rather than a matter
of taste:

  deterministic  near-zero baseline, so binomial variance is tiny and a rise
                 is detectable in a couple of hundred samples. Gate on these.

  quality        mid-range proportion measured through a noisy judge, so you
                 need thousands of samples. Never gate on these. Shadow them,
                 and alert on drift across releases where samples accumulate.

Deliberately refuses to gate on an underpowered metric rather than reporting a
green light that means nothing. A meaningless green light is worse than no
gate, because it gets read as evidence.
"""
from dataclasses import dataclass

from .canary import rise_detectable


@dataclass
class GateResult:
    passed: bool
    reason: str
    underpowered: list[str]


@dataclass
class CanaryGate:
    baseline: dict[str, float]      # deterministic metric -> baseline rate
    min_samples: int = 200

    def evaluate(self, observed: dict[str, float], n: int) -> GateResult:
        if n < self.min_samples:
            return GateResult(False, f"only {n} samples, need {self.min_samples}", [])

        underpowered, failures = [], []
        for metric, base in self.baseline.items():
            if metric not in observed:
                continue
            floor = rise_detectable(base, n)
            rise = observed[metric] - base

            # A rise above the detectable floor IS the significance test.
            # An earlier version of this multiplied the floor by a tolerance,
            # which let a jump from 0.1% to 5% schema failures pass. There is
            # now a test for that.
            if rise > floor:
                failures.append(
                    f"{metric} rose {rise:.2%}, above the {floor:.2%} detectable at n={n}")
            elif rise > 0:
                underpowered.append(
                    f"{metric} rose {rise:.2%} but {n} samples can only see {floor:.2%}")

        if failures:
            return GateResult(False, "; ".join(failures), underpowered)
        return GateResult(True, f"no deterministic regression at n={n}", underpowered)
