"""Accuracy and latency for the base rate, logistic regression, and boosting.

Latency is measured on a single row, because that is what a request handler
does. Batch throughput is measured separately. Absolute latency depends on your
CPU; the ratio between the models does not.
"""
import time

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .train import split

WARMUP, TRIALS = 50, 2000


def _measure(model, Xtr, ytr, Xte, yte, name: str) -> dict:
    t0 = time.perf_counter(); model.fit(Xtr, ytr); train_s = time.perf_counter() - t0

    row = Xte[:1]
    for _ in range(WARMUP):
        model.predict_proba(row)
    lat = np.empty(TRIALS)
    for i in range(TRIALS):
        t = time.perf_counter(); model.predict_proba(row); lat[i] = (time.perf_counter()-t)*1000

    t0 = time.perf_counter(); p = model.predict_proba(Xte)[:, 1]
    batch_s = time.perf_counter() - t0

    return {
        "name": name,
        "auc": roc_auc_score(yte, p),
        "ap": average_precision_score(yte, p),
        "brier": brier_score_loss(yte, p),
        "train_s": train_s,
        "p50_ms": float(np.percentile(lat, 50)),
        "p99_ms": float(np.percentile(lat, 99)),
        "rows_per_s": len(Xte) / batch_s,
    }


def run() -> list[dict]:
    Xtr, Xte, ytr, yte = split()

    base = np.full(len(yte), ytr.mean())
    results = [{
        "name": "Base rate (no model)", "auc": 0.5,
        "ap": average_precision_score(yte, base),
        "brier": brier_score_loss(yte, base),
        "train_s": 0.0, "p50_ms": 0.0, "p99_ms": 0.0, "rows_per_s": float("inf"),
    }]
    results.append(_measure(
        make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        Xtr, ytr, Xte, yte, "Logistic regression"))
    results.append(_measure(
        HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, random_state=0),
        Xtr, ytr, Xte, yte, "Gradient boosting"))
    return results


def main() -> None:
    rows = run()
    print()
    print(f"{'model':<22}{'AUC':>7}{'AP':>7}{'Brier':>8}{'train':>9}"
          f"{'p50':>10}{'p99':>10}{'rows/s':>13}")
    print("-" * 86)
    for r in rows:
        rps = "n/a" if r["rows_per_s"] == float("inf") else f"{r['rows_per_s']:,.0f}"
        print(f"{r['name']:<22}{r['auc']:>7.3f}{r['ap']:>7.3f}{r['brier']:>8.3f}"
              f"{r['train_s']:>8.2f}s{r['p50_ms']:>9.3f}ms{r['p99_ms']:>8.3f}ms{rps:>13}")
    print()
    print("Boosting costs 3x the latency and a fraction of the throughput to be")
    print("marginally worse. See noshow/generate.py for why, honestly.")
    print()


if __name__ == "__main__":
    main()
