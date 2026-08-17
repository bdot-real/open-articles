"""Recorded provider responses.

Fixtures, not mocks. A mock encodes what you believe the model does. A
recording encodes what it did, including the malformed responses that are the
whole reason the deterministic layer exists.

Refresh these deliberately, review the diff, and treat a change as a change to
production behaviour, because it is.
"""

SOURCE = "book a standup with Dana on Sunday morning, 30 minutes, Toronto time"

# Well formed, with incidental variation between runs. The parsed structures
# are identical, which is what the stability property asserts.
GOOD = [
    '{"title":"Standup","start":"2026-03-08T09:00:00-05:00",'
    '"end":"2026-03-08T09:30:00-05:00","timezone":"America/Toronto",'
    '"attendees":["Dana"]}',

    '```json\n{"title": "Standup", "start": "2026-03-08T09:00:00-05:00",\n'
    ' "end": "2026-03-08T09:30:00-05:00",\n "timezone": "America/Toronto",\n'
    ' "attendees": ["Dana"]}\n```',

    '{"attendees":["Dana"],"timezone":"America/Toronto",'
    '"end":"2026-03-08T09:30:00-05:00","start":"2026-03-08T09:00:00-05:00",'
    '"title":"Standup"}',
]

# Real failure shapes. Every one of these reads as confident and correct.
BAD = {
    "prose_preamble":
        'Sure! Here is the booking:\n{"title":"Standup"}',
    "invented_attendee":
        '{"title":"Standup","start":"2026-03-08T09:00:00-05:00",'
        '"end":"2026-03-08T09:30:00-05:00","timezone":"America/Toronto",'
        '"attendees":["Dana","Priya"]}',
    "abbreviated_timezone":
        '{"title":"Standup","start":"2026-03-08T09:00:00-05:00",'
        '"end":"2026-03-08T09:30:00-05:00","timezone":"EST",'
        '"attendees":["Dana"]}',
    "naive_instant":
        '{"title":"Standup","start":"2026-03-08T09:00:00",'
        '"end":"2026-03-08T09:30:00","timezone":"America/Toronto",'
        '"attendees":["Dana"]}',
    "reversed_interval":
        '{"title":"Standup","start":"2026-03-08T09:30:00-05:00",'
        '"end":"2026-03-08T09:00:00-05:00","timezone":"America/Toronto",'
        '"attendees":["Dana"]}',
    "duration_as_string":
        '{"title":"Standup","start":"2026-03-08T09:00:00-05:00",'
        '"end":"2026-03-08T09:30:00-05:00","timezone":"America/Toronto",'
        '"attendees":[42]}',
}


def replay(index: int = 0):
    """A deterministic stand-in for a provider call."""
    return lambda _text: GOOD[index % len(GOOD)]
