"""Shared types for the OSSS conformance suite."""
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Appointment:
    """An appointment stored as UTC instants.

    Spec rule 2: stored instants are always UTC. Local time is a presentation
    concern and never enters the storage layer.
    """
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        for instant in (self.start, self.end):
            if instant.tzinfo is None or instant.utcoffset().total_seconds() != 0:
                raise ValueError("Appointment instants must be UTC-aware")
        if self.end < self.start:
            raise ValueError("end precedes start")


def utc(y: int, mo: int, d: int, h: int = 0, mi: int = 0) -> datetime:
    """Build a UTC instant. Test convenience only."""
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)
