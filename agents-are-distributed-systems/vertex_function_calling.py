"""Google. Gemini Enterprise Agent Platform, function calling.

Function declarations are JSON schemas with no effect field, same as Bedrock.
The classification goes in a side table you maintain, and the important part is
that registering a tool without an entry should fail rather than default to
something convenient.
"""
from agent.executor import Effect

EFFECTS: dict[str, Effect] = {
    "search_availability": Effect.READ,
    "validate_booking": Effect.IDEMPOTENT,
    "create_booking": Effect.MUTATING,
    "cancel_booking": Effect.MUTATING,
}


def effect_for(function_name: str) -> Effect:
    """Refuse rather than guess.

    A default of MUTATING would be safe but would quietly disable retries on
    reads. A default of READ would be fast and would double-book people. There
    is no good default, so require the decision.
    """
    try:
        return EFFECTS[function_name]
    except KeyError:
        raise KeyError(
            f"{function_name!r} has no effect classification. Add it to "
            f"EFFECTS before registering the tool: retry behaviour cannot be "
            f"decided without it."
        ) from None
