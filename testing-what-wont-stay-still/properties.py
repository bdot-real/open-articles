"""The middle layer: invariants that hold regardless of wording.

These run against recorded model responses, so they are as deterministic as any
other test. The model is called once when the fixture is recorded, never during
a test run.

That is the whole trick. Record, then assert. A property test that calls a
provider is not a property test, it is a flaky integration test wearing a hat.
"""
from collections.abc import Callable

from .extract import Booking, ExtractionError, parse


def is_stable(raw_responses: list[str], source: str) -> bool:
    """Same input, same structure, across recorded runs.

    Note what this does NOT require: identical text. Two responses may differ
    in whitespace, key order or field ordering and still be stable, because the
    assertion is on the parsed structure.
    """
    parsed = []
    for raw in raw_responses:
        try:
            parsed.append(parse(raw, source))
        except ExtractionError:
            return False
    return all(b == parsed[0] for b in parsed)


def is_invariant_under(transform: Callable[[str], str], source: str,
                       invoke: Callable[[str], str]) -> bool:
    """Irrelevant changes to the input must not move the output.

    Appending a signature, changing capitalisation, or adding a pleasantry
    should not change an extracted appointment. When it does, the feature is
    keying on something it should not be.
    """
    try:
        a = parse(invoke(source), source)
        mutated = transform(source)
        b = parse(invoke(mutated), mutated)
    except ExtractionError:
        return False
    return (a.start, a.end, a.timezone) == (b.start, b.end, b.timezone)


def is_idempotent(booking: Booking, reserialise: Callable[[Booking], str],
                  invoke: Callable[[str], str]) -> bool:
    """Feeding the output back in should reproduce it.

    A cheap and surprisingly sharp check. Extraction that is not idempotent is
    usually inventing detail on each pass.
    """
    text = reserialise(booking)
    try:
        return parse(invoke(text), text) == booking
    except ExtractionError:
        return False
