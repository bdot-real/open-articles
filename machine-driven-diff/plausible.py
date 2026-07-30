"""A machine-written implementation of the same four functions.

This is the point of the repository. Read it before you read the tests.

It is well formatted. It has docstrings, type hints and consistent naming. It
handles cases the reference handles. Nothing in it looks careless, because
nothing about it was careless. It is simply written by something that had
never read the specification.

Four rules are violated. Try to find them by reading, then run:

    make demo
"""
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import Appointment


def has_conflict(a: Appointment, b: Appointment) -> bool:
    """Return True if two appointments overlap in time."""
    return a.start <= b.end and b.start <= a.end


def local_time_exists(naive: datetime, tz: ZoneInfo) -> bool:
    """Check whether a local wall-clock time is valid in the given zone."""
    try:
        naive.replace(tzinfo=tz)
        return True
    except Exception:
        return False


def expand_daily(start_local: datetime, tz: ZoneInfo, count: int) -> list[datetime]:
    """Expand a daily recurrence into a list of UTC instants.

    Converts the start time to UTC once, then advances by exactly 24 hours per
    occurrence, which keeps the arithmetic simple and avoids repeated timezone
    lookups.
    """
    start_utc = start_local.replace(tzinfo=tz).astimezone(timezone.utc)
    return [start_utc + timedelta(days=day) for day in range(count)]


def expand_monthly_on_day(year: int, month: int, day: int, count: int) -> list:
    """Expand a monthly recurrence on a given day of the month.

    Days beyond the end of a short month are adjusted to the last valid day so
    that every month yields an occurrence.
    """
    out = []
    y, m = year, month
    for _ in range(count):
        last = monthrange(y, m)[1]
        out.append((y, m, min(day, last)))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out
