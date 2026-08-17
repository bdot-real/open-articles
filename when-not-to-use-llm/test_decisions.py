"""Tests for the claims the article makes.

These exist so that "you can check every number" is true rather than a figure
of speech. Anything asserted in the article that is deterministic is pinned
here.
"""
import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from noshow.calibration import max_gap, table
from noshow.decisions import COLLISION, SLOT_VALUE, net_value, overbook_threshold
from noshow.generate import generate
from noshow.train import fit, split


@pytest.fixture(scope="module")
def fitted():
    X, y = generate()
    from sklearn.model_selection import train_test_split
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.25, random_state=0, stratify=y)
    model = fit(Xtr, ytr)
    return model, Xte, ytr, yte, model.predict_proba(Xte)[:, 1]


# ------------------------------------------------------------------ accuracy
def test_model_beats_the_base_rate_by_a_useful_margin(fitted):
    _, _, _, yte, p = fitted
    assert roc_auc_score(yte, p) > 0.70


def test_model_is_small_enough_to_ship_in_process(fitted):
    import pickle
    model, *_ = fitted
    assert len(pickle.dumps(model)) < 5_000, "should be kilobytes, not megabytes"


# --------------------------------------------------------------- calibration
def test_predictions_are_calibrated(fitted):
    """The property the whole argument rests on.

    Ranking well is not enough. AUC is invariant to any monotone transform of
    the scores, so a model can rank perfectly and still be unusable for
    thresholding. This asserts the number means what it says.
    """
    _, _, _, yte, p = fitted
    assert max_gap(table(p, yte)) < 0.05


def test_calibration_breaks_under_a_monotone_transform(fitted):
    """Squaring the probabilities leaves AUC untouched and destroys calibration.

    This is the failure mode you cannot detect with AUC alone, and it is the
    shape of what you get from a model that emits plausible-looking numbers.
    """
    _, _, _, yte, p = fitted
    squashed = p ** 2
    assert roc_auc_score(yte, squashed) == pytest.approx(roc_auc_score(yte, p))
    assert max_gap(table(squashed, yte)) > 0.05


# ----------------------------------------------------------------- decisions
def test_threshold_formula_matches_the_break_even_point():
    t = overbook_threshold(SLOT_VALUE, COLLISION)
    # At the threshold, expected gain equals expected loss.
    assert t * SLOT_VALUE == pytest.approx((1 - t) * COLLISION)
    assert t == pytest.approx(0.684, abs=0.001)


def test_derived_threshold_beats_intuitive_ones(fitted):
    """The article's central claim, asserted rather than asserted-at."""
    _, _, ytr, yte, p = fitted
    derived = net_value(p, yte, overbook_threshold())["net"]
    half = net_value(p, yte, 0.50)["net"]
    base = net_value(p, yte, float(ytr.mean()))["net"]

    assert derived > 0, "the economically-derived threshold makes money"
    assert half < 0, "0.5 loses money"
    assert base < half, "acting on everything above the base rate is worse still"
    assert derived - half > 40_000


def test_threshold_moves_with_the_economics():
    """Change the cost of a collision and the threshold follows."""
    cheap = overbook_threshold(slot_value=120, collision=30)
    dear = overbook_threshold(slot_value=120, collision=900)
    assert cheap < 0.25 < dear
    assert dear > 0.85, "when collisions are expensive, act only on near-certainty"


def test_net_value_is_zero_when_nothing_is_actioned(fitted):
    _, _, _, yte, p = fitted
    assert net_value(p, yte, 1.01)["net"] == 0.0


# -------------------------------------------------------------------- hybrid
def test_extraction_is_cached_by_note_and_version():
    from hybrid.extract import cache_key, extract, fake_invoke

    calls = {"n": 0}
    def counting(prompt):
        calls["n"] += 1
        return fake_invoke(prompt)

    cache: dict = {}
    note = "Patient relies on daughter for a lift."
    extract(note, counting, cache)
    extract(note, counting, cache)
    assert calls["n"] == 1, "identical notes must not be re-extracted"
    assert cache_key(note) != cache_key(note + " ")


def test_extraction_failure_degrades_rather_than_raises():
    from hybrid.extract import extract

    def broken(_):
        raise RuntimeError("provider down")

    flags = extract("any note", broken, {})
    assert flags == {"transport_difficulty": 0, "anxiety_signal": 0,
                     "caregiver_dependent": 0}
