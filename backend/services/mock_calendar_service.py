"""Deterministic calendar fixtures for graph development."""

from datetime import date, datetime, time, timedelta
import re
from typing import Any


_EVENTS: tuple[dict[str, Any], ...] = (
    {
        "id": "event-001",
        "title": "Product stand-up",
        "day": "today",
        "time": "10:00 AM",
        "participants": ["product@example.com"],
    },
    {
        "id": "event-002",
        "title": "Launch readiness review",
        "day": "tomorrow",
        "time": "4:00 PM",
        "participants": ["alice@example.com"],
    },
)


def list_events(day: str | None = None) -> list[dict[str, Any]]:
    events = (event for event in _EVENTS if day is None or event["day"] == day)
    return [dict(event) for event in events]


def _resolve_date(value: str | None) -> date:
    today = datetime.now().date()
    lowered = (value or "today").strip().casefold()
    if lowered == "today":
        return today
    if lowered == "tomorrow":
        return today + timedelta(days=1)
    match = re.fullmatch(
        r"(?:on\s+)?(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        lowered,
    )
    if match:
        weekdays = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        delta = (weekdays[match.group(2)] - today.weekday()) % 7
        if match.group(1) and delta == 0:
            delta = 7
        return today + timedelta(days=delta)
    natural_date = re.sub(
        r"\b(?:by|before|on|due|no\s+later\s+than)\b",
        "",
        lowered,
    ).strip()
    for date_format in ("%B %d, %Y", "%b %d, %Y", "%B %d", "%b %d"):
        try:
            parsed = datetime.strptime(natural_date, date_format).date()
            if "%Y" not in date_format:
                parsed = parsed.replace(year=today.year)
                if parsed < today:
                    parsed = parsed.replace(year=today.year + 1)
            return parsed
        except ValueError:
            continue
    try:
        return date.fromisoformat(lowered)
    except ValueError:
        return today


def _fixture_events_for_date(target: date) -> list[dict[str, Any]]:
    today = datetime.now().date()
    day_name = "today" if target == today else "tomorrow" if target == today + timedelta(days=1) else None
    return list_events(day_name) if day_name else []


def find_available_slots(
    before_date: str,
    duration_minutes: int = 30,
    working_hours: tuple[int, int] = (9, 18),
) -> list[dict[str, Any]]:
    """Return the first three deterministic open slots on or before a deadline."""

    deadline = _resolve_date(before_date)
    today = datetime.now().date()
    duration = max(15, min(int(duration_minutes or 30), 480))
    opening_hour, closing_hour = working_hours
    if deadline < today or opening_hour >= closing_hour:
        return []

    slots: list[dict[str, Any]] = []
    current_day = today
    while current_day <= deadline and len(slots) < 3:
        day_start = datetime.combine(current_day, time(opening_hour))
        day_end = datetime.combine(current_day, time(closing_hour))
        busy_times = {
            datetime.strptime(str(event["time"]), "%I:%M %p").time()
            for event in _fixture_events_for_date(current_day)
            if event.get("time") and event["time"] != "All day"
        }
        candidate = day_start
        while candidate + timedelta(minutes=duration) <= day_end and len(slots) < 3:
            if candidate.time() not in busy_times:
                slots.append(
                    {
                        "date": current_day.isoformat(),
                        "time": candidate.strftime("%I:%M %p").lstrip("0"),
                        "duration_minutes": duration,
                    }
                )
            candidate += timedelta(minutes=30)
        current_day += timedelta(days=1)
    return slots
