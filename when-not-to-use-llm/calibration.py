"""Does a predicted probability mean what it says?

This is the property that separates a model you can make decisions with from a
model that merely ranks well. AUC is invariant to any monotone transform of the
scores, so a model can rank perfectly and still be useless for thresholding.
"""
import pickle
from pathlib import Path

import numpy as np

from .train import split


def table(p: np.ndarray, y: np.ndarray, bins: int = 10, min_n: int = 30) -> list[dict]:
    out = []
    edges = np.linspace(0, 1, bins + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum() < min_n:
            continue
        out.append({"lo": lo, "hi": hi, "n": int(m.sum()),
                    "predicted": float(p[m].mean()), "observed": float(y[m].mean())})
    return out


def max_gap(rows: list[dict]) -> float:
    return max(abs(r["predicted"] - r["observed"]) for r in rows)


def main() -> None:
    _, Xte, _, yte = split()
    with Path("data/model.pkl").open("rb") as f:
        p = pickle.load(f).predict_proba(Xte)[:, 1]

    rows = table(p, yte)
    print()
    print(f"{'predicted band':<18}{'n':>7}{'predicted':>12}{'observed':>11}{'gap':>9}")
    print("-" * 57)
    for r in rows:
        gap = r["predicted"] - r["observed"]
        band = f"{r['lo']:.1f} - {r['hi']:.1f}"
        print(f"{band:<18}{r['n']:>7}{r['predicted']:>12.3f}"
              f"{r['observed']:>11.3f}{gap:>+9.3f}")
    print()
    print(f"largest gap across bands: {max_gap(rows):.3f}")
    print("When it says 0.75, three quarters of those appointments are no-shows.")
    print()


if __name__ == "__main__":
    main()
