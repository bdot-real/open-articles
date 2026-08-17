"""Open source. No platform at all.

Two lines of modelling. Serialises to 1.5 KB, so it ships inside the service:
no endpoint, no network hop, no availability dependency, no idle cost.

The trap is that "no infrastructure" is true on day one and false by month six,
when you need retraining, drift detection, versioning and rollback. That is
what the managed platforms sell, and it is a fair sale. Start here anyway, and
move when you feel the specific pain rather than in anticipation of it.
"""
import pickle
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from noshow.train import split


def main() -> None:
    Xtr, Xte, ytr, yte = split()
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(Xtr, ytr)

    blob = pickle.dumps(model)
    Path("data/model.pkl").write_bytes(blob)
    print(f"{len(blob):,} bytes. Ship it in the container.")


if __name__ == "__main__":
    main()
