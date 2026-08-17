"""A booking extractor: free text in, structured booking out.

The unit under test in the rest of this repository. The model does one job,
turning language into a structure, and everything after that boundary is
ordinary deterministic code that can be tested at 100 percent.

Which is the point. Most of what teams try to test with a judge lives on this
side of the boundary and does not need one.
"""
import json
import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

VALID_ZONES = available_timezones()


class ExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class Booking:
    title: str
    start: datetime
    end: datetime
    timezone: str
    attendees: tuple[str, ...]


def parse(raw: str, source_text: str) -> Booking:
    """Turn a model response into a Booking, or refuse.

    Every check here is deterministic. None of it needs a model to verify, and
    all of it catches a class of failure that a judge would score as fine
    because the prose around it reads well.
    """
    try:
        payload = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        raise ExtractionError(f"not valid json: {e}") from e

    missing = {"title", "start", "end", "timezone", "attendees"} - payload.keys()
    if missing:
        raise ExtractionError(f"missing fields: {sorted(missing)}")

    tz = payload["timezone"]
    # Legacy aliases like "EST" and "MST" are present in the tz database and
    # are not acceptable here: they are fixed offsets carrying no DST rules, so
    # a recurring appointment stored against one silently stops shifting with
    # the clocks. Require the region/city form.
    if tz not in VALID_ZONES or "/" not in tz:
        raise ExtractionError(f"not a region/city IANA zone: {tz!r}")

    try:
        start = datetime.fromisoformat(payload["start"])
        end = datetime.fromisoformat(payload["end"])
    except (TypeError, ValueError) as e:
        raise ExtractionError(f"unparseable instant: {e}") from e

    if start.tzinfo is None or end.tzinfo is None:
        raise ExtractionError("instants must carry an offset")
    if end <= start:
        raise ExtractionError("end must follow start")

    attendees = tuple(payload["attendees"])
    if not all(isinstance(a, str) for a in attendees):
        raise ExtractionError("attendees must be strings")

    # Grounding, checked without a judge. An attendee who does not appear in
    # the source text was invented, and no amount of fluent prose makes that
    # acceptable. This is the check people assume needs an LLM.
    lowered = source_text.lower()
    invented = [a for a in attendees if a.lower() not in lowered]
    if invented:
        raise ExtractionError(f"attendees not present in source: {invented}")

    return Booking(payload["title"], start, end, tz, attendees)


def _strip_fences(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def duration_minutes(b: Booking) -> int:
    return int((b.end - b.start).total_seconds() // 60)


def local_times(b: Booking) -> tuple[datetime, datetime]:
    z = ZoneInfo(b.timezone)
    return b.start.astimezone(z), b.end.astimezone(z)
