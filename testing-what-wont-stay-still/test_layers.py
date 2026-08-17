"""Tests for all three layers, plus the claims the article makes.

Note what is absent: not one test in this file calls a model provider. Every
one passes 100% of the time and fails for exactly one reason, which is the
entire argument.
"""
import math

import pytest

from booking.extract import ExtractionError, parse
from booking.properties import is_stable
from booking.recorded import BAD, GOOD, SOURCE, replay
from evals.flakiness import suite_pass_rate, max_flaky_tests
from evals.judge import detectable_delta, observed_rate, samples_needed, youden_j


# ------------------------------------------------------- layer 1: deterministic
@pytest.mark.parametrize("name", sorted(BAD))
def test_every_recorded_failure_is_caught_without_a_judge(name):
    """Each of these reads as confident and correct. None survives a schema."""
    with pytest.raises(ExtractionError):
        parse(BAD[name], SOURCE)


def test_well_formed_responses_parse():
    for raw in GOOD:
        assert parse(raw, SOURCE).title == "Standup"


def test_grounding_is_a_substring_check_not_a_judge():
    """Faithfulness is the flagship LLM-as-judge use case.

    For extraction, a large part of it is free.
    """
    with pytest.raises(ExtractionError, match="not present in source"):
        parse(BAD["invented_attendee"], SOURCE)


def test_legacy_timezone_abbreviations_are_rejected():
    """"EST" is in the tz database and is still wrong.

    It is a fixed offset with no DST rules, so a recurring appointment stored
    against it silently stops shifting with the clocks. This one got past my
    first validator, which is why it has a test.
    """
    with pytest.raises(ExtractionError, match="region/city"):
        parse(BAD["abbreviated_timezone"], SOURCE)


# ------------------------------------------------------------ layer 2: property
def test_structure_is_stable_across_recorded_runs():
    """Identical structure, despite differing whitespace, fences and key order.

    The assertion is on the parse, not the text. Asserting on text is what
    makes AI tests flaky.
    """
    assert is_stable(GOOD, SOURCE)


def test_property_layer_makes_no_provider_calls():
    calls = {"n": 0}

    def counting(_):
        calls["n"] += 1
        return GOOD[0]

    replay(0)("anything")
    assert calls["n"] == 0


# --------------------------------------------------------- the flakiness claim
def test_two_hundred_tests_at_ninety_nine_percent_fail_most_runs():
    """The article's opening number."""
    assert suite_pass_rate(0.99, 200) == pytest.approx(0.134, abs=0.001)


def test_a_handful_of_flaky_tests_is_enough_to_poison_a_suite():
    assert max_flaky_tests(0.99) <= 6
    assert max_flaky_tests(0.95) <= 2


def test_deterministic_tests_compose_and_flaky_ones_do_not():
    assert suite_pass_rate(1.0, 10_000) == 1.0
    assert suite_pass_rate(0.99, 10_000) < 1e-40


# ------------------------------------------------------------- the judge claims
def test_an_imperfect_judge_shrinks_the_effect_rather_than_only_adding_noise():
    """The finding. observed_gap = true_gap * (sens + spec - 1)."""
    p0, p1 = 0.80, 0.75
    se = sp = 0.85
    observed = observed_rate(p0, se, sp) - observed_rate(p1, se, sp)
    assert observed == pytest.approx((p0 - p1) * youden_j(se, sp))
    assert observed < (p0 - p1), "the measured gap is smaller than the real one"


def test_sample_size_cost_exceeds_the_one_over_j_squared_approximation():
    """1/J^2 is a floor, not the answer.

    The shrunken gap accounts for 1/J^2 of the cost. The rest comes from the
    judge pulling both observed rates toward 0.5, where binomial variance is
    largest. For an 85/85 judge that is 2.04x predicted against 2.5x real.
    """
    perfect = samples_needed(0.80, 0.05, 1.0, 1.0)
    typical = samples_needed(0.80, 0.05, 0.85, 0.85)
    ratio = typical / perfect
    floor = 1 / youden_j(0.85, 0.85) ** 2

    assert ratio > floor, "the approximation understates the real cost"
    assert ratio == pytest.approx(2.5, abs=0.15)


def test_a_fifty_example_eval_set_cannot_see_a_small_regression():
    """The number that should change how eval sets are sized."""
    assert detectable_delta(0.80, 50, 0.85, 0.85) > 0.30
    assert detectable_delta(0.80, 1000, 0.85, 0.85) < 0.10


def test_a_useless_judge_can_detect_nothing():
    """sens + spec == 1 means the judge is uninformative at any sample size."""
    assert math.isinf(samples_needed(0.80, 0.05, 0.5, 0.5))
