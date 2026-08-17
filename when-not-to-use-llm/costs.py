"""Cost arithmetic: scoring through an LLM against a classical endpoint.

The article concedes that this is the weakest of the three arguments, and the
small-model column is why. Conceding it is what makes the calibration argument
land instead of reading as advocacy.
"""
REQ_PER_DAY = 200_000
DAYS = 30

PROMPT_TOKENS = 420      # instructions plus 13 features rendered as text
OUTPUT_TOKENS = 12       # just the number

# Illustrative rates in dollars per million tokens. Replace with current pricing.
TIERS = {"frontier": (3.00, 15.00), "small": (0.15, 0.60)}
ENDPOINT_MONTHLY = 62.0  # a small always-on managed endpoint, illustrative


def llm_monthly(tier: str) -> tuple[float, float]:
    inr, outr = TIERS[tier]
    per = PROMPT_TOKENS * inr / 1e6 + OUTPUT_TOKENS * outr / 1e6
    return per, per * REQ_PER_DAY * DAYS


def main() -> None:
    total = REQ_PER_DAY * DAYS
    print()
    print(f"At {REQ_PER_DAY:,} scores/day over {DAYS} days ({total:,} scores):")
    print()
    print(f"{'path':<26}{'per call':>12}{'monthly':>13}{'vs classical':>14}")
    print("-" * 65)
    for tier in ("frontier", "small"):
        per, mo = llm_monthly(tier)
        print(f"{'LLM, ' + tier + ' tier':<26}${per:>11.6f}"
              f"{'$' + format(mo, ',.0f'):>13}{mo / ENDPOINT_MONTHLY:>13,.0f}x")
    print(f"{'Classical endpoint':<26}{'~0 marginal':>12}"
          f"{'$' + format(ENDPOINT_MONTHLY, ',.0f'):>13}{1:>13}x")
    print()
    print("139x against frontier is real. 7x against a small model is $400 a month,")
    print("which plenty of teams would pay to avoid owning a training pipeline.")
    print("Argue purely on token cost and you lose that argument.")
    print()


if __name__ == "__main__":
    main()
