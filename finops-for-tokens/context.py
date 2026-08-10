"""The attribution context.

Every model call carries one of these. This is the entire difference between
"the AI bill is up 40 percent" and "the summarization feature for one tenant is
up 40 percent, and here is the change that did it".

Add it on day one. Cost allocation tags are not retroactive, so the month you
most want to understand is the month you have no data for.
"""
import uuid
from dataclasses import dataclass, field, asdict


@dataclass(frozen=True)
class CallContext:
    tenant_id: str
    feature: str
    user_id: str | None = None
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    environment: str = "prod"

    def as_tags(self) -> dict:
        """Flat string map, which is what every provider's metadata field wants."""
        return {k: str(v) for k, v in asdict(self).items() if v is not None}

    def budget_key(self, day: str) -> str:
        return f"spend:{self.environment}:{self.tenant_id}:{day}"
