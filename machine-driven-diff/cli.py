"""Entry point for the spec-anchored review pass.

    python -m review.cli --base main --head HEAD --backend local

Exit code is always 0. This pass is advisory. Gating a merge on a
non-deterministic reviewer trains contributors to rewrite correct code in order
to appease a machine, which is worse than not running it at all.
"""
import argparse
import os
import sys

from review.backends import get_backend
from review.prompt import build_prompt

NO_VIOLATIONS = "NO VIOLATIONS FOUND"


def main() -> int:
    p = argparse.ArgumentParser(description="Spec-anchored PR review")
    p.add_argument("--base", default=os.environ.get("BASE_SHA", "origin/main"))
    p.add_argument("--head", default=os.environ.get("HEAD_SHA", "HEAD"))
    p.add_argument("--backend", default=os.environ.get("REVIEW_BACKEND", "local"))
    p.add_argument("--dry-run", action="store_true",
                   help="Print the assembled prompt and exit. Costs nothing.")
    args = p.parse_args()

    prompt = build_prompt(args.base, args.head)

    if args.dry_run:
        print(prompt)
        return 0

    result = get_backend(args.backend)(prompt).strip()

    if result == NO_VIOLATIONS:
        print("No spec violations found.")
        return 0

    print("## Spec conformance notes\n")
    print(result)
    print("\n---\n_Advisory only. Not a merge gate. "
          "The conformance suite is the gate._")
    return 0


if __name__ == "__main__":
    sys.exit(main())
