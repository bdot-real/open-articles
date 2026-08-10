"""Tests for the parts that stop money leaving.

These matter more than they look. A budget guard that fails open is worse than
no budget guard, because it buys you the belief that you are protected.
"""
import pytest

from finops.budget import BudgetExceeded, BudgetGuard
from finops.context import CallContext
from finops.pricing import RATES, Usage, cost
from finops.store import InMemoryStore
from finops.client import BoundedAgentLoop, InstrumentedClient


@pytest.fixture
def guard():
    return BudgetGuard(InMemoryStore(), limits={"acme": 1.00}, default_limit=0.10)


@pytest.fixture
def ctx():
    return CallContext(tenant_id="acme", feature="ticket_summary", user_id="u1")


def test_reserve_allows_a_call_within_budget(guard, ctx):
    assert guard.reserve(ctx, "frontier", input_tokens=1000) > 0


def test_reserve_blocks_once_the_limit_is_reached(guard, ctx):
    guard.settle(ctx, "frontier", Usage(input_tokens=200_000, output_tokens=50_000))
    with pytest.raises(BudgetExceeded):
        guard.reserve(ctx, "frontier", input_tokens=1000)


def test_unknown_tenants_get_the_default_not_unlimited(guard):
    other = CallContext(tenant_id="unknown-tenant", feature="chat")
    assert guard.limit_for("unknown-tenant") == 0.10
    guard.settle(other, "frontier", Usage(input_tokens=100_000, output_tokens=10_000))
    with pytest.raises(BudgetExceeded):
        guard.reserve(other, "frontier", input_tokens=500)


def test_estimate_exceeds_actual_so_the_breaker_does_not_fail_open(guard, ctx):
    """The reserve must over-estimate. Under-estimating makes it a suggestion."""
    reserved = guard.reserve(ctx, "frontier", input_tokens=1000)
    actual = guard.settle(ctx, "frontier", Usage(input_tokens=1000, output_tokens=300))
    assert reserved > actual


def test_spend_accumulates_per_tenant_not_globally(guard):
    a = CallContext(tenant_id="acme", feature="chat")
    b = CallContext(tenant_id="globex", feature="chat")
    guard.settle(a, "frontier", Usage(input_tokens=10_000))
    assert guard.spent(a) > 0
    assert guard.spent(b) == 0


def test_spend_is_scoped_by_environment(guard):
    prod = CallContext(tenant_id="acme", feature="chat", environment="prod")
    stg = CallContext(tenant_id="acme", feature="chat", environment="staging")
    guard.settle(prod, "frontier", Usage(input_tokens=10_000))
    assert guard.spent(stg) == 0, "a staging load test must not exhaust prod budget"


# ------------------------------------------------------------------ pricing
def test_cached_input_is_cheaper_than_fresh_input():
    fresh = cost("frontier", Usage(input_tokens=10_000))
    cached = cost("frontier", Usage(cache_read_tokens=10_000))
    assert cached < fresh / 5, "caching should change the order of magnitude"


def test_output_costs_more_than_input():
    assert RATES["frontier"].output > RATES["frontier"].input


# ------------------------------------------------------------------ agent loop
def _fake_invoke(messages, tags):
    return "ok", Usage(input_tokens=3000, output_tokens=400)


def test_agent_loop_stops_at_the_spend_cap_before_the_iteration_cap():
    guard = BudgetGuard(InMemoryStore(), limits={"acme": 100.0})
    client = InstrumentedClient(guard, _fake_invoke, tier="frontier")
    loop = BoundedAgentLoop(client, max_iterations=100, max_spend=0.10)

    result = loop.run(
        CallContext(tenant_id="acme", feature="agent"),
        step=lambda i: ([{"role": "user", "content": "keep going"}], 3000, False),
    )
    assert result["stopped"] == "spend_cap"
    assert result["iterations"] < 100


def test_agent_loop_respects_completion():
    guard = BudgetGuard(InMemoryStore(), limits={"acme": 100.0})
    client = InstrumentedClient(guard, _fake_invoke, tier="frontier")
    loop = BoundedAgentLoop(client, max_iterations=10, max_spend=100.0)

    result = loop.run(
        CallContext(tenant_id="acme", feature="agent"),
        step=lambda i: ([{"role": "user", "content": "x"}], 100, i >= 3),
    )
    assert result["stopped"] == "completed"
    assert result["iterations"] == 3
