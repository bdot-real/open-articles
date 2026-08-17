"""How much of a real failure catalogue needs a judge?

The claim under test: most of what teams point a judge at is deterministically
checkable, and the judge is only needed for the residue.

Each entry below is a real failure mode of a structured extraction feature,
tagged with the cheapest layer that can catch it.
"""
from collections import Counter

FAILURES = [
    # (failure mode, cheapest layer that catches it)
    ("Response is not valid JSON",                         "deterministic"),
    ("Required field missing",                             "deterministic"),
    ("Timezone is not an IANA identifier",                 "deterministic"),
    ("Instant has no UTC offset",                          "deterministic"),
    ("End time precedes start time",                       "deterministic"),
    ("Attendee not present in the source text",            "deterministic"),
    ("Duration exceeds the configured maximum",            "deterministic"),
    ("Wrapped in markdown fences",                         "deterministic"),
    ("Numeric field returned as a string",                 "deterministic"),
    ("Enum value outside the allowed set",                 "deterministic"),
    ("Tool called with malformed arguments",               "deterministic"),
    ("Retrieved chunk not cited in the answer",            "deterministic"),
    ("Citation points to a document not retrieved",        "deterministic"),
    ("PII appears in the output",                          "deterministic"),
    ("Output exceeds the token budget",                    "deterministic"),

    ("Same input yields a different structure across runs", "property"),
    ("Reordering attendees changes the parsed result",      "property"),
    ("Adding irrelevant text changes the extracted time",   "property"),
    ("Extraction is not idempotent when re-fed its output", "property"),
    ("Confidence rises when the input gets vaguer",         "property"),

    ("Answer is factually wrong despite correct grounding", "judge"),
    ("Tone is inappropriate for the audience",              "judge"),
    ("Answer is technically true but misleading",           "judge"),
    ("Refuses a request it should have handled",            "judge"),
]


def main():
    counts = Counter(layer for _, layer in FAILURES)
    total = len(FAILURES)

    print(f"\n{total} failure modes of one structured extraction feature.\n")
    print(f"{'layer':<16}{'count':>7}{'share':>8}  {'cost to run':<22}{'reliability':<12}")
    print("-" * 68)
    meta = {
        "deterministic": ("free, no model call", "100%"),
        "property":      ("cached responses", "100%"),
        "judge":         ("model call per sample", "measured, ~85%"),
    }
    for layer in ("deterministic", "property", "judge"):
        c = counts[layer]
        cost, rel = meta[layer]
        print(f"{layer:<16}{c:>7}{c/total:>8.0%}  {cost:<22}{rel:<12}")

    print()
    d = counts["deterministic"] + counts["property"]
    print(f"{d/total:.0%} of these need no judge and no statistics. They are")
    print("ordinary tests that pass 100% of the time and fail for one reason.")
    print()
    print(f"The remaining {counts['judge']/total:.0%} is where judges belong, and where the")
    print("sample size arithmetic in judge.py starts to matter.")
    print()
    print("Most teams invert this: a small judge-based eval set covering")
    print("everything, and no deterministic layer at all.\n")


if __name__ == "__main__":
    main()
