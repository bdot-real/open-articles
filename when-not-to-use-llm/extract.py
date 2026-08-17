"""The hybrid pattern: the LLM turns language into features, at write time.

The seam matters more than either half.

Extraction runs once per note, when the note is written, not once per score.
That single choice changes three things at once:

    latency  a second is invisible at write time and fatal in a request handler
    cost     once per note, not once per score, and the result caches forever
    blast    a provider outage delays enrichment; it does not stop scoring

The decision layer downstream stays classical, so it keeps its calibration,
determinism, sub-millisecond latency and audit trail.

Drift warning, which is the part people miss. The moment the extraction model
is upgraded, the meaning of these columns shifts and the classifier is
consuming features whose distribution moved with no code change on your side.
EXTRACTOR_VERSION is part of the cache key for exactly that reason, and a
version bump should be treated as a retraining trigger.
"""
import hashlib
import json
from collections.abc import Callable

EXTRACTOR_VERSION = "v1"

SCHEMA = {
    "transport_difficulty": "1 if the note mentions difficulty getting to appointments",
    "anxiety_signal": "1 if the note indicates anxiety or reluctance about the visit",
    "caregiver_dependent": "1 if attendance depends on another person",
}

PROMPT = """Extract three binary flags from the clinical scheduling note below.

{schema}

Reply with JSON only, no prose, using exactly these keys and values of 0 or 1.

NOTE:
{note}
"""


def cache_key(note: str) -> str:
    h = hashlib.sha256(note.encode()).hexdigest()[:16]
    return f"noteftr:{EXTRACTOR_VERSION}:{h}"


def extract(note: str, invoke: Callable[[str], str], cache: dict | None = None) -> dict:
    """Return the three flags. `invoke` is any callable taking a prompt.

    Failure returns zeros rather than raising. A missing enrichment should
    degrade the prediction slightly, never block the appointment from being
    scored at all.
    """
    cache = cache if cache is not None else {}
    key = cache_key(note)
    if key in cache:
        return cache[key]

    schema = "\n".join(f"- {k}: {v}" for k, v in SCHEMA.items())
    try:
        raw = invoke(PROMPT.format(schema=schema, note=note))
        parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        result = {k: int(bool(parsed.get(k, 0))) for k in SCHEMA}
    except Exception:
        result = {k: 0 for k in SCHEMA}

    cache[key] = result
    return result


def fake_invoke(prompt: str) -> str:
    """Deterministic stand-in so the demo runs with no credentials."""
    note = prompt.split("NOTE:\n", 1)[-1].lower()
    return json.dumps({
        "transport_difficulty": int(any(w in note for w in
                                        ("bus", "lift", "transport", "drive", "far"))),
        "anxiety_signal": int(any(w in note for w in
                                  ("anxious", "nervous", "scared", "worried"))),
        "caregiver_dependent": int(any(w in note for w in
                                       ("daughter", "son", "carer", "caregiver", "wife",
                                        "husband", "accompan"))),
    })


def main() -> None:
    notes = [
        "Patient relies on daughter for a lift, no bus route nearby.",
        "Routine follow up, no concerns raised.",
        "Very anxious about the procedure, asked to reschedule twice already.",
        "Patient relies on daughter for a lift, no bus route nearby.",   # repeat
    ]
    cache: dict = {}
    calls = {"n": 0}

    def counting_invoke(p: str) -> str:
        calls["n"] += 1
        return fake_invoke(p)

    print()
    print(f"{'note':<58}{'transp':>8}{'anx':>6}{'carer':>7}")
    print("-" * 79)
    for n in notes:
        f = extract(n, counting_invoke, cache)
        print(f"{n[:56]:<58}{f['transport_difficulty']:>8}"
              f"{f['anxiety_signal']:>6}{f['caregiver_dependent']:>7}")
    print()
    print(f"{len(notes)} notes, {calls['n']} model calls. The repeat was cached.")
    print("At write time, so none of this is in the scoring path.")
    print()


if __name__ == "__main__":
    main()
