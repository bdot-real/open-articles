"""Stage, verify, commit.

The deterministic test layer from the previous article, applied at runtime.

Rolling back a prompt does not undo what it wrote, so the only thing that
bounds the damage of a bad deploy is whether a wrong output could reach durable
state without a check. Produce, run the cheap checks, and commit only what
passes. Everything else goes to quarantine.

Two things fall out for free:

  the quarantine depth is the fastest alarm you have, because it moves within
  seconds of a bad deploy and needs no judge and no statistics

  remediation becomes a queue you work through rather than a corruption you
  have to go find
"""
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Check = Callable[[Any], str | None]      # returns a reason, or None if it passes


@dataclass
class Quarantine:
    items: list[tuple[Any, str]] = field(default_factory=list)

    def add(self, record: Any, reason: str) -> None:
        self.items.append((record, reason))

    @property
    def depth(self) -> int:
        return len(self.items)

    def reasons(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for _, reason in self.items:
            out[reason] = out.get(reason, 0) + 1
        return out


@dataclass
class TwoPhaseWriter:
    """Nothing reaches `committed` without passing every check."""
    checks: list[Check]
    committed: list[Any] = field(default_factory=list)
    quarantine: Quarantine = field(default_factory=Quarantine)

    def write(self, record: Any) -> bool:
        for check in self.checks:
            reason = check(record)
            if reason is not None:
                self.quarantine.add(record, reason)
                return False
        self.committed.append(record)
        return True

    @property
    def quarantine_rate(self) -> float:
        total = len(self.committed) + self.quarantine.depth
        return self.quarantine.depth / total if total else 0.0
