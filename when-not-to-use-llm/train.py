"""Fit the model. Two lines of modelling, and that is the point."""
import pickle
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def split(data_dir: str = "data", seed: int = 0):
    X = np.load(Path(data_dir) / "X.npy")
    y = np.load(Path(data_dir) / "y.npy")
    return train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)


def fit(X_train, y_train):
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(
        X_train, y_train)


def main() -> None:
    Xtr, Xte, ytr, yte = split()
    model = fit(Xtr, ytr)
    out = Path("data/model.pkl")
    with out.open("wb") as f:
        pickle.dump(model, f)
    print(f"trained on {len(ytr):,} rows")
    print(f"serialised to {out}: {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
