"""Retrying a tool call that already worked.

A timeout is not a failure. It is an UNKNOWN OUTCOME. The request may have
reached the service, been processed, and committed, with only the response
lost. Retrying then performs the operation twice.

Service-to-service RPC solved this decades ago with idempotency keys. Agent
frameworks hand the caller role to a non-deterministic component and, by
default, ship none of it.

This matters more for agents than for ordinary RPC for two reasons. Agents
retry more, because their failure rate is higher. And agents call tools that
book, charge, email and delete, because that is the entire point of giving
them tools.
"""
import numpy as np

rng = np.random.default_rng(7)

TIMEOUT_RATE = 0.04        # of calls, response lost
ALREADY_COMMITTED = 0.55   # of timeouts, the operation actually succeeded
TRIALS = 200_000


def call(idempotency_key: str | None, ledger: set, max_retries: int) -> tuple[bool, int]:
    """Returns (completed, side_effects_applied)."""
    effects = 0
    for _ in range(max_retries + 1):
        timed_out = rng.random() < TIMEOUT_RATE
        committed = (not timed_out) or (rng.random() < ALREADY_COMMITTED)

        if committed:
            if idempotency_key is None:
                effects += 1                       # no dedupe, apply again
            elif idempotency_key not in ledger:
                ledger.add(idempotency_key)
                effects += 1                       # first time only
        if not timed_out:
            return True, effects
    return False, effects


def measure(use_keys: bool, max_retries: int, trials: int = TRIALS):
    dupes = 0
    for i in range(trials):
        ledger: set = set()
        key = f"task-{i}" if use_keys else None
        _, effects = call(key, ledger, max_retries)
        dupes += max(0, effects - 1)
    return dupes / trials


def main():
    print(f"\nTimeouts on {TIMEOUT_RATE:.0%} of calls. "
          f"{ALREADY_COMMITTED:.0%} of those already committed server-side.\n")

    print("Duplicate side effects per task, single tool call:\n")
    print(f"{'retries':>9}{'no key':>12}{'with key':>11}")
    print("-" * 32)
    for r in (1, 2, 3, 5):
        print(f"{r:>9}{measure(False, r):>11.2%}{measure(True, r):>11.2%}")

    print("\nA 10 step agent, 2 retries per step, 100,000 tasks a day:\n")
    per_call = measure(False, 2, 60_000)
    for steps, label in ((1, "single tool call"), (10, "10 step agent")):
        daily = per_call * steps * 100_000
        print(f"  {label:<20}{daily:>10,.0f} duplicate operations per day")

    print("\nIf those operations are appointment bookings, that is the number of")
    print("customers double booked. If they are charges, it is worse. With")
    print("idempotency keys it is zero, and the key is one field.\n")

    print("The uncomfortable part: none of this appears in a success metric.")
    print("The task completed. The agent reported success. It was right.\n")


if __name__ == "__main__":
    main()
