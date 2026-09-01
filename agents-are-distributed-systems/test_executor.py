"""Tests for the safeguards, which are the point of the repository.

The simulations are illustrative. These are not: they pin behaviour that
decides whether a customer gets charged twice.
"""
import pytest

from agent.executor import (BudgetExhausted, Effect, Executor, StepBudget, Tool,
                            idempotency_key)


def ok(_):
    return {"ok": True}


def timeout(_):
    raise TimeoutError("gateway timeout")


def bad_args(args):
    if args.get("tz") == "EST":
        raise ValueError("not a region/city zone")
    return {"ok": True}


def flaky_connection(state):
    def fn(_):
        state["n"] += 1
        if state["n"] < 3:
            raise ConnectionError("connection reset")
        return {"ok": True, "attempts": state["n"]}
    return fn


# ------------------------------------------------------------- effect classes
def test_mutating_timeout_refuses_to_retry():
    """The headline safeguard. A timeout is an unknown outcome, and repeating
    a mutation on an unknown outcome is how you double-book someone."""
    ex = Executor(tools={"book": Tool("book", Effect.MUTATING, timeout)})
    with pytest.raises(RuntimeError, match="MUTATING"):
        ex.run_step("t1", 1, "book", {"slot": "09:00"})


def test_read_timeout_is_retried_freely():
    state = {"n": 0}

    def fn(_):
        state["n"] += 1
        if state["n"] == 1:
            raise TimeoutError("slow")
        return {"rows": 3}

    ex = Executor(tools={"search": Tool("search", Effect.READ, fn)})
    assert ex.run_step("t1", 1, "search", {"q": "x"}) == {"rows": 3}
    assert state["n"] == 2


def test_reads_get_no_idempotency_key():
    """Keys cost a lookup and buy nothing for a read."""
    ex = Executor(tools={"search": Tool("search", Effect.READ, ok)})
    ex.run_step("t1", 1, "search", {"q": "x"})
    assert ex.trace[0].idempotency_key is None


def test_mutations_get_an_idempotency_key():
    ex = Executor(tools={"book": Tool("book", Effect.MUTATING, ok)})
    ex.run_step("t1", 1, "book", {"slot": "09:00"})
    assert ex.trace[0].idempotency_key is not None


# --------------------------------------------------------------- idempotency
def test_key_is_stable_for_the_same_logical_operation():
    a = idempotency_key("t1", 1, "book", {"slot": "09:00", "who": "dana"})
    b = idempotency_key("t1", 1, "book", {"who": "dana", "slot": "09:00"})
    assert a == b, "key ordering must not matter"


def test_key_changes_when_the_operation_changes():
    """Derived from arguments, so a replan correctly gets a NEW key while a
    blind retry correctly reuses the old one. Most hand-rolled versions hash a
    request id instead and get this backwards."""
    base = idempotency_key("t1", 1, "book", {"slot": "09:00"})
    assert idempotency_key("t1", 1, "book", {"slot": "10:00"}) != base
    assert idempotency_key("t1", 2, "book", {"slot": "09:00"}) != base
    assert idempotency_key("t2", 1, "book", {"slot": "09:00"}) != base


def test_replaying_a_seen_key_applies_no_second_effect():
    calls = {"n": 0}

    def counting(_):
        calls["n"] += 1
        return {"booking": "b-1"}

    ex = Executor(tools={"book": Tool("book", Effect.IDEMPOTENT, counting)})
    ex.run_step("t1", 1, "book", {"slot": "09:00"})
    result = ex.run_step("t1", 1, "book", {"slot": "09:00"})

    assert calls["n"] == 1, "the underlying tool must run exactly once"
    assert result == {"deduplicated": True}


# -------------------------------------------------------------------- replan
def test_persistent_failure_without_a_replan_hook_fails_loudly():
    """Better than silently burning three model calls reproducing a bug."""
    ex = Executor(tools={"validate": Tool("validate", Effect.IDEMPOTENT, bad_args)})
    with pytest.raises(RuntimeError, match="persistently"):
        ex.run_step("t1", 1, "validate", {"tz": "EST"})


def test_replan_changes_the_context_and_succeeds():
    ex = Executor(tools={"validate": Tool("validate", Effect.IDEMPOTENT, bad_args)})
    out = ex.run_step("t1", 1, "validate", {"tz": "EST"},
                      replan=lambda note: {"tz": "America/Toronto"})
    assert out == {"ok": True}
    assert [e.outcome for e in ex.trace] == ["persistent", "ok"]


def test_transient_failure_is_retried_without_replanning():
    ex = Executor(tools={"sync": Tool("sync", Effect.READ,
                                      flaky_connection({"n": 0}))})
    assert ex.run_step("t1", 1, "sync", {})["attempts"] == 3


# ------------------------------------------------------------------- budgets
def test_step_budget_stops_an_unbounded_loop():
    b = StepBudget(max_steps=3, max_spend=100.0)
    with pytest.raises(BudgetExhausted, match="step budget"):
        for _ in range(10):
            b.charge()


def test_spend_budget_binds_independently_of_steps():
    """A step cap alone does not bound spend, because a single step's cost
    varies by orders of magnitude with accumulated context."""
    b = StepBudget(max_steps=1000, max_spend=0.05)
    with pytest.raises(BudgetExhausted, match="spend budget"):
        for _ in range(10):
            b.charge(cost=0.02)


# --------------------------------------------------------------------- trace
def test_every_attempt_is_traced():
    ex = Executor(tools={"validate": Tool("validate", Effect.IDEMPOTENT, bad_args)})
    ex.run_step("t1", 1, "validate", {"tz": "EST"},
                replan=lambda n: {"tz": "America/Toronto"})
    assert len(ex.trace) == 2
    assert {e.attempt for e in ex.trace} == {0, 1}
    assert all(e.elapsed_ms >= 0 for e in ex.trace)
