"""Synthetic appointment data with a fully documented signal structure.

Synthetic on purpose, so that anyone can reproduce every number in the article
without access to patient data. The generative process is written out below
rather than hidden, which matters for one specific reason:

    The data is mostly log-linear by construction. That is why logistic
    regression edges out gradient boosting in the benchmark. Real no-show data
    carries more interaction structure and trees usually win on it.

Saying this plainly costs a more impressive-looking result and buys the only
thing worth having, which is a number someone can trust. The latency, model
size and calibration findings are properties of the method and do not depend
on this choice.
"""
import json
from pathlib import Path

import numpy as np

from .features import COLUMNS

N = 40_000
SEED = 7


def generate(n: int = N, seed: int = SEED):
    rng = np.random.default_rng(seed)

    lead_days      = rng.gamma(2.0, 7.0, n).clip(0, 120)
    prior_noshows  = rng.poisson(0.6, n).clip(0, 12)
    prior_attended = rng.poisson(4.0, n).clip(0, 40)
    age            = rng.normal(44, 16, n).clip(18, 95)
    hour           = rng.integers(8, 18, n)
    dow            = rng.integers(0, 5, n)
    sms_reminder   = rng.binomial(1, 0.72, n)
    distance_km    = rng.gamma(2.0, 6.0, n).clip(0, 90)
    is_new_patient = rng.binomial(1, 0.22, n)
    reschedules    = rng.poisson(0.35, n).clip(0, 6)
    copay          = rng.choice([0, 15, 30, 50], n, p=[.45, .25, .2, .1])
    slot_minutes   = rng.choice([15, 30, 45, 60], n, p=[.4, .35, .15, .1])

    hist_rate = prior_noshows / np.maximum(prior_noshows + prior_attended, 1)

    # The true log-odds. Mostly additive and monotone, with two interactions.
    logit = (
        -2.35
        + 1.05 * np.log1p(lead_days) * 0.42     # diminishing effect of lead time
        + 3.10 * hist_rate                       # past behaviour dominates
        + 0.55 * is_new_patient
        + 0.42 * reschedules
        - 0.62 * sms_reminder
        + 0.013 * distance_km
        - 0.016 * (age - 44)
        + 0.35 * (hour >= 16)                    # late slots
        + 0.30 * (dow == 0)                      # Mondays
        + 0.010 * copay
        + 0.9 * (hist_rate > 0.4) * (lead_days > 30)   # interaction
        - 0.5 * sms_reminder * (hist_rate < 0.15)      # interaction
    )
    y = rng.binomial(1, 1 / (1 + np.exp(-logit)))

    X = np.column_stack([
        lead_days, prior_noshows, prior_attended, age, hour, dow, sms_reminder,
        distance_km, is_new_patient, reschedules, copay, slot_minutes, hist_rate,
    ])
    return X, y


def main(out: str = "data") -> None:
    d = Path(out); d.mkdir(exist_ok=True)
    X, y = generate()
    np.save(d / "X.npy", X); np.save(d / "y.npy", y)
    (d / "columns.json").write_text(json.dumps(COLUMNS, indent=2))
    print(f"n={len(y):,}  no-show rate={y.mean():.3f}  features={X.shape[1]}")


if __name__ == "__main__":
    main()
