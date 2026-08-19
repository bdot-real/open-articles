"""Rolling back a prompt does not roll back what it wrote.

The thing code deploys taught us to optimise is rollback speed. For a prompt
change that is close to irrelevant, because the damage is not the outage. The
damage is the records you persisted while you were wrong, and reverting the
prompt leaves every one of them in the database.

So blast radius is:

    bad_records = request_rate * time_to_detect * fraction_wrong

Note which term is missing. Time to ROLL BACK barely appears. A five second
revert behind a two day detection is a two day incident.
"""
DAILY = 100_000
FRACTION_WRONG = 0.06          # the bad prompt is subtly wrong, not broken
REMEDIATION_PER_RECORD = 0.40  # reprocess, reconcile, notify


DETECTION = [
    ("Deterministic canary alarm", 5 / 60,      "schema failure rate spikes"),
    ("Latency or error-rate alarm", 0.5,        "only if it breaks loudly"),
    ("Shadow comparison, hourly",  1.0,         "full traffic, no blast radius"),
    ("Judge-based canary, 5%",     30.0,        "underpowered until it is not"),
    ("Weekly quality review",      84.0,        "the honest default"),
    ("Customer reports it",        120.0,       "how most of these are found"),
]


def bad_records(hours: float) -> int:
    return int(DAILY * (hours / 24) * FRACTION_WRONG)


def main():
    print(f"\n{DAILY:,} requests/day. A prompt change makes "
          f"{FRACTION_WRONG:.0%} of outputs subtly wrong.")
    print("Outputs are persisted, so a revert does not undo them.\n")
    print(f"{'detection mechanism':<30}{'MTTD':>9}{'bad records':>14}"
          f"{'remediation':>14}")
    print("-" * 67)
    for name, hours, _ in DETECTION:
        n = bad_records(hours)
        print(f"{name:<30}{hours:>7.1f}h{n:>14,}"
              f"{'$' + format(n * REMEDIATION_PER_RECORD, ',.0f'):>14}")

    fast, slow = bad_records(5 / 60), bad_records(120)
    print()
    print(f"Ratio between the fastest and the honest default: {slow/fast:,.0f}x")
    print()
    print("Rollback speed is not in this table because it does not move it.")
    print("A five second revert behind a five day detection is a five day incident.")
    print()

    # What actually helps: not persisting until you are confident.
    print("The other lever, which is architectural rather than operational:\n")
    for label, quarantined in [("Write directly to the store", 0.0),
                               ("Quarantine low-confidence for review", 0.55),
                               ("Two-phase: stage, verify, commit", 0.92)]:
        n = int(bad_records(120) * (1 - quarantined))
        print(f"  {label:<38}{n:>9,} bad records"
              f"{'  $' + format(n * REMEDIATION_PER_RECORD, ',.0f'):>14}")
    print()
    print("Same five day detection in all three rows. The difference is whether")
    print("a wrong output could reach durable state without a check.\n")


if __name__ == "__main__":
    main()
