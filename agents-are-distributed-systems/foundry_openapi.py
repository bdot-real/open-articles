"""Azure. AI Foundry Agent Service, tools as OpenAPI.

The most useful of the four for this problem, because HTTP already has the
vocabulary. GET is a read, PUT is idempotent, POST is not, and Idempotency-Key
is a well-trodden header convention.

If your tools are honest REST, the effect classification is already written
down and the executor can read it off the method instead of a side table.
"""
from agent.executor import Effect

# The mapping the article argues you should not have to write, because the
# protocol already encodes it.
METHOD_EFFECT = {
    "get": Effect.READ,
    "head": Effect.READ,
    "options": Effect.READ,
    "put": Effect.IDEMPOTENT,
    "delete": Effect.IDEMPOTENT,   # idempotent by spec, though not by habit
    "post": Effect.MUTATING,
    "patch": Effect.MUTATING,
}


def effects_from_spec(openapi: dict) -> dict[str, Effect]:
    """Derive the effect of every operation from its HTTP method.

    Honest REST gets you the classification for free. Tools that POST for
    everything get everything classified as MUTATING, which is the safe
    default and also a useful smell.
    """
    out = {}
    for path, methods in openapi.get("paths", {}).items():
        for method, op in methods.items():
            if method.lower() in METHOD_EFFECT:
                name = op.get("operationId") or f"{method}:{path}"
                out[name] = METHOD_EFFECT[method.lower()]
    return out


def request_headers(idempotency_key: str | None) -> dict:
    return {"Idempotency-Key": idempotency_key} if idempotency_key else {}
