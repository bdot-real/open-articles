"""Why retrying an agent step is not like retrying a network call.

This is a model, not a measurement of any real agent. The parameters are
assumptions and the value is in the structure and the sensitivity, not the
absolute numbers. Change them at the top and see what survives.

The distinction the model captures:

  transient failure   the tool timed out, the network blipped, the provider
                      was briefly overloaded. Retrying the same call with the
                      same context is likely to work.

  persistent failure  the model misread the context, chose the wrong tool, or
                      built a malformed argument. The cause is IN the context,
                      so retrying with the same context reproduces it.

Distributed systems retry logic assumes the first kind. Agent failures are
substantially the second kind, and that changes what recovery has to do.
"""
import numpy as np

rng = np.random.default_rng(11)

STEP_SUCCESS = 0.97      # per-step success on a clean attempt
PERSISTENT_SHARE = 0.60  # of failures, the share caused by context rather than luck
REPLAN_RECOVERY = 0.70   # chance that rebuilding context clears a persistent cause
TRIALS = 40_000


def run_task(steps: int, max_retries: int, strategy: str,
             persistent_share: float = PERSISTENT_SHARE) -> tuple[bool, int]:
    """Returns (completed, attempts_consumed)."""
    attempts = 0
    for _ in range(steps):
        persistent = False
        for attempt in range(max_retries + 1):
            attempts += 1
            if attempt == 0:
                if rng.random() < STEP_SUCCESS:
                    break
                persistent = rng.random() < persistent_share
            else:
                if persistent:
                    if strategy == "replan" and rng.random() < REPLAN_RECOVERY:
                        persistent = False          # context rebuilt, cause cleared
                    else:
                        continue                    # same context, same failure
                if rng.random() < STEP_SUCCESS:
                    break
        else:
            return False, attempts
    return True, attempts


def measure(steps: int, max_retries: int, strategy: str, trials: int = TRIALS,
            persistent_share: float = PERSISTENT_SHARE):
    out = [run_task(steps, max_retries, strategy, persistent_share)
           for _ in range(trials)]
    done = np.array([o[0] for o in out])
    used = np.array([o[1] for o in out])
    return done.mean(), used.mean()


def main():
    print(f"\nPer-step success {STEP_SUCCESS:.0%}. "
          f"{PERSISTENT_SHARE:.0%} of failures are caused by context.\n")

    print("Task completion, no retries at all (the p^n floor):\n")
    print(f"{'steps':>7}{'completion':>13}")
    print("-" * 21)
    for k in (1, 3, 5, 10, 20, 40):
        print(f"{k:>7}{STEP_SUCCESS ** k:>12.1%}")

    print("\nAdding retries. 10 step task.\n")
    print(f"{'retries':>9}{'blind retry':>14}{'replan':>10}{'gap':>9}")
    print("-" * 43)
    for r in (0, 1, 2, 3, 5):
        blind, _ = measure(10, r, "retry")
        replan, _ = measure(10, r, "replan")
        print(f"{r:>9}{blind:>13.1%}{replan:>10.1%}{replan-blind:>+9.1%}")

    print("\nWhy the gap: with 2 retries, a persistent failure gets three")
    print("attempts against the same context and fails all three by")
    print("construction. Blind retry only ever rescues the transient share.\n")

    print("Sensitivity. How much of the benefit depends on the assumption?\n")
    print(f"{'persistent share':>18}{'blind':>9}{'replan':>9}{'gap':>9}")
    print("-" * 45)
    for share in (0.2, 0.4, 0.6, 0.8, 0.95):
        b, _ = measure(10, 2, "retry", 15_000, share)
        rp, _ = measure(10, 2, "replan", 15_000, share)
        print(f"{share:>17.0%}{b:>9.1%}{rp:>9.1%}{rp-b:>+9.1%}")
    print("\nThe recommendation holds across the whole range, and the size of")
    print("the win scales with how context-caused your failures are.\n")


if __name__ == "__main__":
    main()
