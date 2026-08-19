"""Tests for every claim the article makes.

No provider is called. Every test passes 100% of the time.
"""
import pytest

from deploy.blast_radius import bad_records
from deploy.canary import detectable, rise_detectable, samples
from deploy.canary_gate import CanaryGate
from deploy.release import Registry, Release, UnpinnedModel
from deploy.two_phase import TwoPhaseWriter

DATED = "sonnet-4-5-20251120"
OLDER = "sonnet-4-5-20250929"


# ---------------------------------------------------------------- the pairing
def test_an_alias_is_refused_at_construction():
    """Aliases are mutable tags. A registry full of them cannot roll back."""
    with pytest.raises(UnpinnedModel):
        Release("extract", "prompt text", "sonnet-4-5")


def test_dated_versions_are_accepted():
    assert Release("extract", "p", DATED).model_version == DATED
    assert Release("extract", "p", "gemini-2-5-pro-20260114-v2")


def test_the_pair_changes_when_either_half_changes():
    """The identifier tracks behaviour, so both halves must move it."""
    base = Release("extract", "prompt A", DATED)
    assert Release("extract", "prompt B", DATED).pair != base.pair
    assert Release("extract", "prompt A", OLDER).pair != base.pair


def test_rollback_unconstrained_can_land_on_a_pairing_that_no_longer_exists():
    """Week three of the article's table, as an executable claim.

    v3 was excellent against the old model and is poor against the new one.
    Asking for the last known good prompt WITHOUT constraining the model
    returns v3, which is worse than the release being rolled back from.
    """
    reg = Registry()
    v3_old = reg.publish(Release("extract", "prompt v3", OLDER))
    reg.observe(v3_old, 0.84)

    v3_new = reg.publish(Release("extract", "prompt v3", DATED))
    reg.observe(v3_new, 0.71)                      # provider moved the alias

    v4 = reg.publish(Release("extract", "prompt v4", DATED))
    reg.observe(v4, 0.82)                          # patched to compensate

    v5 = reg.publish(Release("extract", "prompt v5", DATED))
    reg.observe(v5, 0.69)                          # bad deploy

    # The lookup a team performs: which prompt version scored best?
    by_label = reg.best_by_prompt_label(threshold=0.80)
    assert by_label.prompt_text == "prompt v3"
    assert reg.quality_of(by_label) == 0.84

    # That 0.84 was earned against a model that no longer answers to the
    # alias. On the model serving today, v3 scores 0.71.
    assert reg.quality_of(v3_new) == 0.71

    # Constrained to the pairing that will actually run, the answer is v4.
    constrained = reg.last_known_good(threshold=0.80, model_version=DATED)
    assert constrained.prompt_text == "prompt v4"

    # And the gap is the whole point: reverting on prompt history alone
    # recovers 2 points, reverting on the pair recovers 13.
    assert reg.quality_of(v3_new) - reg.quality_of(v5) == pytest.approx(0.02)
    assert reg.quality_of(constrained) - reg.quality_of(v5) == pytest.approx(0.13)


# ----------------------------------------------------------------- the canary
def test_a_one_hour_five_percent_canary_cannot_see_a_quality_regression():
    """The article's second finding."""
    n = samples(100_000, 0.05, 1)
    assert n == 208
    assert detectable(0.80, n, 0.85, 0.85) > 0.15


def test_the_same_window_can_see_a_rare_event_rise():
    """Binomial variance collapses near zero, so rare events are cheap."""
    n = samples(100_000, 0.05, 1)
    assert rise_detectable(0.001, n) < 0.05


def test_one_hour_of_shadow_matches_a_full_day_of_canary():
    """The recommendation, stated accurately.

    An earlier draft claimed shadow beats canary outright at these settings.
    It does not: 5% of a day is 5,000 samples against shadow's 4,166 in an
    hour. The real claim is that shadow compresses a day of waiting into an
    hour at zero blast radius, and pulls ahead from there.
    """
    shadow_1h = detectable(0.80, samples(100_000, 1.0, 1), 0.85, 0.85)
    canary_1d = detectable(0.80, samples(100_000, 0.05, 24), 0.85, 0.85)
    assert shadow_1h == pytest.approx(canary_1d, abs=0.01)

    shadow_6h = detectable(0.80, samples(100_000, 1.0, 6), 0.85, 0.85)
    canary_1w = detectable(0.80, samples(100_000, 0.05, 168), 0.85, 0.85)
    assert shadow_6h <= canary_1w + 0.005, "six hours of shadow matches a week of canary"


# ------------------------------------------------------------------- the gate
def test_gate_fails_on_a_detectable_deterministic_regression():
    """An earlier version of the gate multiplied the detectable floor by a
    tolerance, which let a jump from 0.1% to 5% schema failures pass. That is
    what this test is for."""
    g = CanaryGate(baseline={"schema_failure_rate": 0.001})
    assert g.evaluate({"schema_failure_rate": 0.05}, 208).passed is False


def test_gate_reports_underpowered_rather_than_silently_passing():
    g = CanaryGate(baseline={"schema_failure_rate": 0.001})
    r = g.evaluate({"schema_failure_rate": 0.0015}, 208)
    assert r.passed is True
    assert r.underpowered, "a rise it cannot see must be surfaced, not hidden"


def test_gate_refuses_to_rule_on_too_few_samples():
    g = CanaryGate(baseline={"schema_failure_rate": 0.001})
    assert g.evaluate({"schema_failure_rate": 0.001}, 20).passed is False


# -------------------------------------------------------------- blast radius
def test_blast_radius_is_driven_by_detection_not_rollback():
    fast, slow = bad_records(5 / 60), bad_records(120)
    assert slow / fast > 1000


def test_two_phase_writing_keeps_bad_records_out_of_durable_state():
    w = TwoPhaseWriter(checks=[
        lambda r: "no timezone" if not r.get("tz") else None,
        lambda r: "end before start" if r["end"] <= r["start"] else None,
    ])
    good = {"tz": "America/Toronto", "start": 0, "end": 1}
    assert w.write(good) is True
    assert w.write({"tz": None, "start": 0, "end": 1}) is False
    assert w.write({"tz": "America/Toronto", "start": 5, "end": 2}) is False

    assert w.committed == [good]
    assert w.quarantine.depth == 2
    assert set(w.quarantine.reasons()) == {"no timezone", "end before start"}


def test_quarantine_rate_is_an_alarm_signal():
    """Quarantine depth moves within seconds of a bad deploy and needs no
    judge, which makes it the fastest detection signal available."""
    w = TwoPhaseWriter(checks=[lambda r: "bad" if r["v"] < 0 else None])
    for v in [1, 1, 1, 1, -1]:
        w.write({"v": v})
    assert w.quarantine_rate == pytest.approx(0.2)
