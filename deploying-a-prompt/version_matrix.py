"""What does "roll back to last known good" mean?

Two things version independently and only one of them is yours.

  your prompt      changes when you deploy
  their model      changes when the provider updates an alias, which is not
                   an event you receive

Behaviour is a function of the pair. So the deployable unit is the pair, and a
system that versions only the prompt cannot answer the rollback question. It
reverts to a prompt that was last known good against a model that no longer
exists at that name.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Release:
    prompt: str
    model: str          # what was actually served
    alias: str          # what was configured
    quality: float
    note: str


# A plausible six weeks. Only two rows are the team's own deploys.
HISTORY = [
    Release("v3", "sonnet-4-5-20250929", "sonnet-4-5", 0.84, "steady state"),
    Release("v3", "sonnet-4-5-20250929", "sonnet-4-5", 0.83, "steady state"),
    Release("v3", "sonnet-4-5-20251120", "sonnet-4-5", 0.71, "provider moved the alias"),
    Release("v4", "sonnet-4-5-20251120", "sonnet-4-5", 0.82, "prompt patched to compensate"),
    Release("v4", "sonnet-4-5-20251120", "sonnet-4-5", 0.82, "steady state"),
    Release("v5", "sonnet-4-5-20251120", "sonnet-4-5", 0.69, "bad deploy, roll back"),
]


def main():
    print("\nSix weeks of a system that pins an alias rather than a version.\n")
    print(f"{'wk':>3}  {'prompt':<7}{'alias':<13}{'served':<24}{'quality':>8}  note")
    print("-" * 84)
    for i, r in enumerate(HISTORY, 1):
        print(f"{i:>3}  {r.prompt:<7}{r.alias:<13}{r.model:<24}{r.quality:>8.2f}  {r.note}")

    print("\nWeek 3 is the interesting one. Nobody deployed. Quality fell 12 points.")
    print("There is no entry in the change log, because there was no change")
    print("on the team's side. This is the hardest incident class in the category.\n")

    current = HISTORY[-1]
    print(f'Week 6 is a bad deploy. "Roll back to last known good" means what?\n')

    naive = next(r for r in reversed(HISTORY[:-1]) if r.quality > 0.80)
    print(f"  Revert the prompt only        -> {naive.prompt} on "
          f"{current.model}, quality ~{naive.quality:.2f}")
    print("     Works here, because v4 was tuned against the model now serving.")

    older = HISTORY[0]
    print(f"  Revert two prompts            -> {older.prompt} on "
          f"{current.model}, quality ~0.71")
    print("     Worse. v3 was good against a model that no longer answers to")
    print("     that alias. The prompt is 'known good' for a pairing gone.")
    print()
    print("  Revert the pair               -> only possible if you pinned the")
    print("     version, recorded which one served each request, and the")
    print("     provider still offers it.")
    print()
    print("Three rules follow, and the first two cost nothing:\n")
    print("  1. Pin the dated model version, never the moving alias.")
    print("  2. Record the served version on every response, next to the")
    print("     prompt hash. Cheap now, and the only way to reconstruct week 3.")
    print("  3. Treat a provider version change as a deploy you did not")
    print("     schedule, and run the same canary against it.\n")


if __name__ == "__main__":
    main()
