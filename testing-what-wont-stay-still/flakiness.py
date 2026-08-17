"""Non-deterministic tests do not compose.

A suite of n independent tests, each passing with probability p, passes as a
whole with probability p^n. That is the entire argument and it is unforgiving.
"""

def suite_pass_rate(p: float, n: int) -> float:
    return p ** n


def max_flaky_tests(p: float, floor: float = 0.95) -> int:
    """How many such tests before the suite is red more often than not."""
    n = 1
    while suite_pass_rate(p, n) >= floor:
        n += 1
    return n


def main():
    print("\nSuite pass rate, by per-test reliability and suite size\n")
    sizes = [10, 50, 100, 200, 500]
    print(f"{'per-test':>10}" + "".join(f"{n:>10}" for n in sizes))
    print("-" * (10 + 10 * len(sizes)))
    for p in (0.999, 0.99, 0.98, 0.95, 0.90):
        row = "".join(f"{suite_pass_rate(p, n):>9.1%}" + " " for n in sizes)
        print(f"{p:>10.3f}" + row)

    print("\nHow many flaky tests before the suite is green less than 95% of runs:\n")
    for p in (0.999, 0.99, 0.98, 0.95, 0.90):
        print(f"  per-test {p:.1%}  ->  {max_flaky_tests(p)} tests")

    print("\nThe deterministic comparison: 200 tests at 100% pass 100% of the time.")
    print("A suite that is red for reasons unrelated to the change is a suite")
    print("nobody reads, which is the same as having no suite.\n")


if __name__ == "__main__":
    main()
