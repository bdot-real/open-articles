"""Reference implementation. Conforms to the spec.

Each function names the rule it satisfies, so a reviewer can check the claim
rather than trust it.
"""
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import Appointment


def has_conflict(a: Appointment, b: Appointment) -> bool:
    """Rule 1: intervals are half-open, [start, end).

    Back-to-back appointments abut. They must not be reported as conflicting.
    """
    return a.start < b.end and b.start < a.end


def local_time_exists(naive: datetime, tz: ZoneInfo) -> bool:
    """True when a wall-clock time occurs on that date in that zone.

    Spring-forward removes an hour, so 02:30 does not exist on the transition
    date in most North American zones.
    """
    aware = naive.replace(tzinfo=tz)
    return aware.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) == naive


def expand_daily(start_local: datetime, tz: ZoneInfo, count: int) -> list[datetime]:
    """Rule 3: daily recurrence is DST-aware.

    Wall-clock time is what recurs, not a fixed UTC offset. Where the wall time
    does not exist on a given date, shift forward past the gap.
    """
    out: list[datetime] = []
    base = start_local.replace(tzinfo=None)
    for day in range(count):
        naive = base + timedelta(days=day)
        if not local_time_exists(naive, tz):
            # Shift by the width of the gap, preserving how far into the
            # missing hour the appointment sat. 02:30 in a one-hour gap
            # becomes 03:30, not 03:00.
            before = (naive - timedelta(days=1)).replace(tzinfo=tz).utcoffset()
            after = (naive + timedelta(days=1)).replace(tzinfo=tz).utcoffset()
            naive += after - before
        out.append(naive.replace(tzinfo=tz).astimezone(timezone.utc))
    return out


def expand_monthly_on_day(year: int, month: int, day: int, count: int) -> list:
    """Rule 4: month-end recurrence skips. It never clamps.

    "The 31st of every month" has no meaning in February. Silently moving it to
    the 28th invents an appointment the user did not schedule.
    """
    out = []
    y, m = year, month
    while len(out) < count:
        if day <= monthrange(y, m)[1]:
            out.append((y, m, day))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out
