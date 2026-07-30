"""Spec-anchored review prompt.

The point of this file is the constraint, not the cleverness. Asking a model
"review this code" produces confident noise about naming conventions. Asking it
"which of these five numbered rules does this diff violate" produces something a
maintainer can act on.

Keep SPEC_RULES short and numbered. Every rule you add dilutes the others.
"""
import subprocess

SPEC_RULES = """
1. Intervals are half-open, [start, end). Back-to-back appointments must not
   be reported as conflicting.
2. Stored instants are UTC. Local time appears only at the presentation
   boundary and must carry an IANA zone id.
3. Recurrence expansion is DST-aware. Wall-clock time recurs, not a fixed UTC
   offset. A rule at 02:30 local must still resolve on days where 02:30 does
   not exist.
4. Month-end recurrence skips months lacking that day. It never clamps to the
   last valid day.
5. Public API changes require a version bump in spec/VERSION.
"""

PROMPT = """You are reviewing a pull request against a published specification.

Report ONLY violations of the numbered rules below. For each violation give the
file, the line, the rule number, and one sentence of explanation. If there are
no violations, reply with exactly: NO VIOLATIONS FOUND

Do not comment on style, naming, formatting, test coverage, or anything else
that is not one of the numbered rules. A maintainer is reading this and their
attention is the scarce resource.

{rules}

--- DIFF ---
{diff}
"""

MAX_DIFF_CHARS = 200_000


def get_diff(base: str, head: str) -> str:
    return subprocess.check_output(
        ["git", "diff", "--unified=3", base, head], text=True
    )


def build_prompt(base: str, head: str) -> str:
    diff = get_diff(base, head)
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n[diff truncated]\n"
    return PROMPT.format(rules=SPEC_RULES, diff=diff)
