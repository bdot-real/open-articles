"""Print the failure-mode table.

    python -m simulate
"""
from finops.pricing import fmt
from simulate.failure_modes import ALL


def main() -> None:
    findings = [f() for f in ALL]

    w = max(len(f.name) for f in findings) + 2
    print()
    print("Token cost failure modes, monthly, at the assumptions in "
          "simulate/failure_modes.py")
    print("Edit those assumptions to model your own traffic.")
    print()
    print(f"{'':<{w}}{'Budgeted':>14}{'Billed':>14}{'Factor':>10}")
    print("-" * (w + 38))
    for f in findings:
        print(f"{f.name:<{w}}{fmt(f.naive):>14}{fmt(f.actual):>14}{f.multiple:>9.1f}x")
    print()
    for f in findings:
        print(f"  {f.name}")
        print(f"    {f.note}")
    print()
    print("None of these require a traffic spike, a bug, or anyone doing "
          "anything unreasonable.")
    print()


if __name__ == "__main__":
    main()
