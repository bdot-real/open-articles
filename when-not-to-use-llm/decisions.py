"""Turning calibrated probabilities into decisions.

The most valuable thing in this repository, and it is arithmetic rather than
modelling. On the same predictions, an economically-derived threshold makes
money and an intuitive one loses it.

You cannot do this with an uncalibrated score. There is no threshold to derive,
because the number does not mean anything on the probability scale.
"""
import pickle
from pathlib import Path

import numpy as np

from .train import split

SLOT_VALUE = 120.0    # revenue recovered when an overbooked slot is used
COLLISION = 260.0     # cost when both patients arrive: overtime, waiting, goodwill


def overbook_threshold(slot_value: float = SLOT_VALUE,
                       collision: float = COLLISION) -> float:
    """Break-even point where expected gain equals expected loss.

        p * slot_value = (1 - p) * collision
        p = collision / (slot_value + collision)
    """
    return collision / (slot_value + collision)


def net_value(p: np.ndarray, y: np.ndarray, threshold: float,
              slot_value: float = SLOT_VALUE,
              collision: float = COLLISION) -> dict:
    act = p > threshold
    recovered = float((act & (y == 1)).sum() * slot_value)
    collisions = float((act & (y == 0)).sum() * collision)
    return {"threshold": threshold, "acted_share": float(act.mean()),
            "recovered": recovered, "collisions": collisions,
            "net": recovered - collisions}


def main() -> None:
    _, Xte, ytr, yte = split()
    with Path("data/model.pkl").open("rb") as f:
        p = pickle.load(f).predict_proba(Xte)[:, 1]

    derived = overbook_threshold()
    candidates = [
        (derived, "derived from the economics"),
        (0.50, "seems reasonable"),
        (float(ytr.mean()), "the base rate"),
    ]

    print()
    print(f"Overbooking. Slot worth ${SLOT_VALUE:.0f}, collision costs ${COLLISION:.0f}.")
    print(f"  threshold = {COLLISION:.0f} / ({SLOT_VALUE:.0f} + {COLLISION:.0f}) "
          f"= {derived:.3f}")
    print()
    print(f"{'threshold':>10}  {'source':<28}{'overbooks':>11}{'net':>14}")
    print("-" * 65)
    for t, label in candidates:
        r = net_value(p, yte, t)
        print(f"{t:>10.3f}  {label:<28}{r['acted_share']:>10.1%}"
              f"{'$' + format(r['net'], ',.0f'):>14}")
    print()
    print(f"Over {len(yte):,} held-out appointments. Same model, same predictions,")
    print("same data. The only difference is where the threshold came from.")
    print()


if __name__ == "__main__":
    main()
