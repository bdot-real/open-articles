"""Open source. MCP tool annotations.

The closest thing to the Effect enum existing as a standard. Tool definitions
carry readOnlyHint, destructiveHint and idempotentHint, which is a real
argument for MCP that has nothing to do with interoperability: it gives a
client somewhere to look before deciding how to retry.

They are hints, and server-supplied, so treat them as a default rather than a
guarantee. A hint you can override beats a field that does not exist.
"""
from agent.executor import Effect

TOOL_DEFINITION = {
    "name": "create_booking",
    "description": "Create an appointment",
    "inputSchema": {"type": "object", "required": ["slot", "attendee"]},
    "annotations": {
        "readOnlyHint": False,
        "destructiveHint": False,     # creates rather than destroys
        "idempotentHint": False,      # repeating it books twice
        "openWorldHint": False,
    },
}


def effect_from_annotations(tool: dict, override: Effect | None = None) -> Effect:
    """Map MCP hints onto the executor's effect classes.

    Defaults to MUTATING when annotations are absent, because the cost of
    wrongly assuming a tool is safe to repeat is unbounded and the cost of
    wrongly assuming it is not is one extra confirmation.
    """
    if override is not None:
        return override

    ann = tool.get("annotations") or {}
    if ann.get("readOnlyHint"):
        return Effect.READ
    if ann.get("idempotentHint"):
        return Effect.IDEMPOTENT
    return Effect.MUTATING
