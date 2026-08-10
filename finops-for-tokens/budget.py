"""Budget enforcement, in two halves.

You cannot know what a request costs before you make it, because output tokens
are unknown until the model stops. So enforcement is:

    reserve  -> an estimate, checked synchronously, before the call
    settle   -> the actual cost, reconciled after the call

Estimate high. An under-estimate turns the circuit breaker into a suggestion.

Everything here is synchronous and in the request path on purpose. Asynchronous
billing data cannot stop spending, only describe it. By the time a cost anomaly
alert fires, the money is gone.
"""
from datetime import date

from .context import CallContext
from .pricing import Usage, cost, fmt
from .store import SpendStore


class BudgetExceeded(Exception):
    def __init__(self, tenant: str, spent: float, limit: float) -> None:
        self.tenant, self.spent, self.limit = tenant, spent, limit
        super().__init__(
            f"tenant {tenant} has spent {fmt(spent)} against a limit of {fmt(limit)}"
        )


class BudgetGuard:
    def __init__(
        self,
        store: SpendStore,
        limits: dict[str, float],
        default_limit: float = 10.0,
        estimate_output_tokens: int = 2000,
        safety_factor: float = 1.25,
    ) -> None:
        self._store = store
        self._limits = limits
        self._default = default_limit
        self._est_output = estimate_output_tokens
        self._safety = safety_factor

    def limit_for(self, tenant: str) -> float:
        return self._limits.get(tenant, self._default)

    def spent(self, ctx: CallContext, day: str | None = None) -> float:
        return self._store.get(ctx.budget_key(day or str(date.today())))

    def reserve(self, ctx: CallContext, tier: str, input_tokens: int) -> float:
        """Pre-flight check. Raises BudgetExceeded before any money is spent."""
        estimate = cost(tier, Usage(
            input_tokens=input_tokens,
            output_tokens=self._est_output,
        )) * self._safety

        already = self.spent(ctx)
        limit = self.limit_for(ctx.tenant_id)
        if already + estimate > limit:
            raise BudgetExceeded(ctx.tenant_id, already, limit)
        return estimate

    def settle(self, ctx: CallContext, tier: str, usage: Usage) -> float:
        """Post-flight reconciliation against the real token counts."""
        actual = cost(tier, usage)
        self._store.add(ctx.budget_key(str(date.today())), actual)
        return actual
