"""The OSSS conformance suite.

These tests belong to the project, not to any contributor. They encode what the
specification requires, which is not the same thing as what any given
implementation happens to do.

Run against either implementation:

    OSSS_IMPL=reference pytest      # passes
    OSSS_IMPL=plausible pytest      # fails, four rules violated
"""
import importlib
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from .models import Appointment, utc

IMPL = os.environ.get("OSSS_IMPL", "reference")
impl = importlib.import_module(f"conformance.{IMPL}")

TORONTO = ZoneInfo("America/Toronto")

# 2026 transitions for America/Toronto.
SPRING_FORWARD = datetime(2026, 3, 8)   # 02:00 to 03:00, so 02:30 does not exist
FALL_BACK = datetime(2026, 11, 1)       # 02:00 to 01:00, so 01:30 happens twice


# ---------------------------------------------------------------- rule 1
def test_back_to_back_appointments_do_not_conflict():
    """[09:00, 10:00) and [10:00, 11:00) abut. They do not overlap."""
    a = Appointment(utc(2026, 6, 1, 9), utc(2026, 6, 1, 10))
    b = Appointment(utc(2026, 6, 1, 10), utc(2026, 6, 1, 11))
    assert impl.has_conflict(a, b) is False
    assert impl.has_conflict(b, a) is False


def test_genuine_overlap_is_detected():
    a = Appointment(utc(2026, 6, 1, 9), utc(2026, 6, 1, 10, 30))
    b = Appointment(utc(2026, 6, 1, 10), utc(2026, 6, 1, 11))
    assert impl.has_conflict(a, b) is True


def test_containment_is_a_conflict():
    outer = Appointment(utc(2026, 6, 1, 9), utc(2026, 6, 1, 17))
    inner = Appointment(utc(2026, 6, 1, 12), utc(2026, 6, 1, 13))
    assert impl.has_conflict(outer, inner) is True


# ---------------------------------------------------------------- rule 3
def test_nonexistent_local_time_is_reported_as_nonexistent():
    """02:30 does not occur on the spring-forward date."""
    gap = SPRING_FORWARD.replace(hour=2, minute=30)
    assert impl.local_time_exists(gap, TORONTO) is False


def test_ordinary_local_time_exists():
    ordinary = datetime(2026, 6, 1, 2, 30)
    assert impl.local_time_exists(ordinary, TORONTO) is True


def test_daily_recurrence_holds_wall_clock_time_across_dst():
    """A 02:30 meeting stays at 02:30 local after the clocks change.

    Adding 24 hours of elapsed time is not the same as adding one day. On the
    transition date 02:30 does not exist, so that occurrence shifts forward.
    """
    start = datetime(2026, 3, 6, 2, 30)
    occurrences = impl.expand_daily(start, TORONTO, 5)
    local = [o.astimezone(TORONTO) for o in occurrences]

    assert [d.strftime("%H:%M") for d in local[:2]] == ["02:30", "02:30"]
    assert local[2].strftime("%H:%M") == "03:30", "gap day shifts past the missing hour"
    assert [d.strftime("%H:%M") for d in local[3:]] == ["02:30", "02:30"], (
        "after the transition the meeting returns to its wall-clock time"
    )


# ---------------------------------------------------------------- rule 4
def test_month_end_recurrence_skips_short_months():
    """The 31st of every month does not occur in February. It is not the 28th."""
    got = impl.expand_monthly_on_day(2026, 1, 31, 4)
    assert got == [(2026, 1, 31), (2026, 3, 31), (2026, 5, 31), (2026, 7, 31)]


def test_day_29_skips_non_leap_february():
    got = impl.expand_monthly_on_day(2026, 1, 29, 3)
    assert (2026, 2, 28) not in got, "clamping invents an appointment"
    assert got == [(2026, 1, 29), (2026, 3, 29), (2026, 4, 29)]


# ---------------------------------------------------------------- rule 2
def test_appointments_reject_naive_datetimes():
    with pytest.raises(ValueError):
        Appointment(datetime(2026, 6, 1, 9), datetime(2026, 6, 1, 10))


def test_appointments_reject_non_utc_offsets():
    local = datetime(2026, 6, 1, 9, tzinfo=TORONTO)
    with pytest.raises(ValueError):
        Appointment(local, local.replace(hour=10))
