"""An instrumented call wrapper.

The provider call is a function you pass in, so this works over Bedrock,
Foundry, Vertex, a self-hosted server, or a fake in tests. The interesting part
is the ordering, not the SDK.
"""
from collections.abc import Callable
from typing import Any

from .budget import BudgetGuard
from .context import CallContext
from .pricing import Usage, fmt


class InstrumentedClient:
    def __init__(
        self,
        guard: BudgetGuard,
        invoke: Callable[[list[dict], dict], tuple[str, Usage]],
        tier: str = "frontier",
        emit: Callable[[str, float, dict], None] | None = None,
    ) -> None:
        self._guard = guard
        self._invoke = invoke
        self._tier = tier
        self._emit = emit or (lambda *a, **k: None)

    def call(
        self,
        ctx: CallContext,
        messages: list[dict],
        estimated_input_tokens: int,
    ) -> tuple[str, float]:
        # 1. Reserve. Synchronous, in the request path, before any spend.
        self._guard.reserve(ctx, self._tier, estimated_input_tokens)

        # 2. Invoke, passing attribution down to the provider's metadata field.
        text, usage = self._invoke(messages, ctx.as_tags())

        # 3. Settle against actual usage, and emit for the dashboards.
        actual = self._guard.settle(ctx, self._tier, usage)
        self._emit("llm.cost", actual, {
            "tenant": ctx.tenant_id,
            "feature": ctx.feature,
            "tier": self._tier,
            "trace_id": ctx.trace_id,
        })
        return text, actual


class BoundedAgentLoop:
    """An agent loop with a spend ceiling.

    An agent without one is an unbounded loop that bills you. Iteration caps
    alone are not enough, because a single iteration's cost varies by orders of
    magnitude depending on how much context it accumulated.
    """

    def __init__(self, client: InstrumentedClient, max_iterations: int = 8,
                 max_spend: float = 0.50) -> None:
        self._client = client
        self._max_iter = max_iterations
        self._max_spend = max_spend

    def run(self, ctx: CallContext, step: Callable[[int], Any]) -> dict:
        spent = 0.0
        for i in range(self._max_iter):
            messages, est_tokens, done = step(i)
            if done:
                return {"iterations": i, "spend": spent, "stopped": "completed"}
            _, cost_of_step = self._client.call(ctx, messages, est_tokens)
            spent += cost_of_step
            if spent >= self._max_spend:
                return {"iterations": i + 1, "spend": spent, "stopped": "spend_cap"}
        return {"iterations": self._max_iter, "spend": spent, "stopped": "iteration_cap"}
