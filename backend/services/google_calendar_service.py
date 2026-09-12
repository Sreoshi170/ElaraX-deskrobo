"""Real Google Calendar operations for the single connected account."""

import re
from datetime import date, datetime, time, timedelta
from typing import Any, Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.config import AETHERBOT_TIMEZONE
from backend.services.google_auth_service import (
    GoogleAuthManager,
    GoogleIntegrationError,
    google_auth_manager,
)


class GoogleCalendarService:
    provider_name = "google"

    def __init__(
        self,
        auth: GoogleAuthManager = google_auth_manager,
        timezone_name: str = AETHERBOT_TIMEZONE,
    ) -> None:
        self.auth = auth
        self.timezone = ZoneInfo(timezone_name)
        self.timezone_name = timezone_name

    def _client(self):
        return build(
            "calendar",
            "v3",
            credentials=self.auth.get_credentials(),
            cache_discovery=False,
        )

    def _day_bounds(self, day: Optional[str]) -> tuple[datetime, datetime]:
        now = datetime.now(self.timezone)
        if day == "tomorrow":
            target = now.date() + timedelta(days=1)
        elif day == "today":
            target = now.date()
        else:
            return now, now + timedelta(days=30)
        start = datetime.combine(target, time.min, tzinfo=self.timezone)
        return start, start + timedelta(days=1)

    def _to_event(self, event: dict[str, Any]) -> dict[str, Any]:
        start_value = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
        end_value = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")
        display_time = "All day"
        if start_value and "T" in start_value:
            start_dt = datetime.fromisoformat(start_value.replace("Z", "+00:00")).astimezone(self.timezone)
            display_time = start_dt.strftime("%I:%M %p").lstrip("0")
        return {
            "id": event["id"],
            "title": event.get("summary") or "Untitled event",
            "description": event.get("description"),
            "start": start_value,
            "end": end_value,
            "time": display_time,
            "participants": [
                attendee.get("email") for attendee in event.get("attendees", []) if attendee.get("email")
            ],
            "html_link": event.get("htmlLink"),
            "meet_link": event.get("hangoutLink"),
            "status": event.get("status"),
            "provider": "google",
        }

    def list_events(
        self,
        day: Optional[str] = None,
        *,
        max_results: int = 20,
        query: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        if start is None or end is None:
            start, end = self._day_bounds(day)
        try:
            response = (
                self._client()
                .events()
                .list(
                    calendarId="primary",
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    maxResults=max(1, min(max_results, 50)),
                    singleEvents=True,
                    orderBy="startTime",
                    q=query,
                )
                .execute()
            )
            return [self._to_event(event) for event in response.get("items", [])]
        except HttpError as exc:
            raise GoogleIntegrationError(
                "Google Calendar could not be read. Check that the Calendar API is enabled and reconnect Google."
            ) from exc

    def find_available_slots(
        self,
        before_date: str,
        duration_minutes: int = 30,
        working_hours: tuple[int, int] = (9, 18),
    ) -> list[dict[str, Any]]:
        """Find the first three free working-hour slots before an email deadline."""

        deadline = self._resolve_date(before_date)
        now = datetime.now(self.timezone)
        if deadline < now.date():
            return []
        duration = max(15, min(int(duration_minutes or 30), 480))
        opening_hour, closing_hour = working_hours
        if opening_hour >= closing_hour:
            return []

        range_start = datetime.combine(now.date(), time.min, tzinfo=self.timezone)
        range_end = datetime.combine(deadline + timedelta(days=1), time.min, tzinfo=self.timezone)
        events = self.list_events(start=range_start, end=range_end, max_results=50)
        busy_ranges: list[tuple[datetime, datetime]] = []
        for event in events:
            start_value = event.get("start")
            end_value = event.get("end")
            if not start_value:
                continue
            try:
                event_start = datetime.fromisoformat(str(start_value).replace("Z", "+00:00"))
                event_end = datetime.fromisoformat(
                    str(end_value or start_value).replace("Z", "+00:00")
                )
                if event_start.tzinfo is None:
                    event_start = event_start.replace(tzinfo=self.timezone)
                if event_end.tzinfo is None:
                    event_end = event_end.replace(tzinfo=self.timezone)
                busy_ranges.append(
                    (event_start.astimezone(self.timezone), event_end.astimezone(self.timezone))
                )
            except (TypeError, ValueError):
                continue

        slots: list[dict[str, Any]] = []
        current_day = now.date()
        while current_day <= deadline and len(slots) < 3:
            day_start = datetime.combine(current_day, time(opening_hour), tzinfo=self.timezone)
            day_end = datetime.combine(current_day, time(closing_hour), tzinfo=self.timezone)
            candidate = day_start
            if current_day == now.date() and candidate < now:
                elapsed_minutes = int((now - day_start).total_seconds() // 60)
                rounded_minutes = ((elapsed_minutes + 29) // 30) * 30
                candidate = day_start + timedelta(minutes=rounded_minutes)
            while candidate + timedelta(minutes=duration) <= day_end and len(slots) < 3:
                candidate_end = candidate + timedelta(minutes=duration)
                if not any(
                    candidate < busy_end and candidate_end > busy_start
                    for busy_start, busy_end in busy_ranges
                ):
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

    def _resolve_date(self, value: Optional[str]) -> date:
        today = datetime.now(self.timezone).date()
        lowered = (value or "").casefold()
        if lowered == "tomorrow":
            return today + timedelta(days=1)
        if lowered in {"today", ""}:
            return today
        weekday_match = re.fullmatch(
            r"(?:on\s+)?(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            lowered,
        )
        if weekday_match:
            weekdays = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            target = weekdays[weekday_match.group(2)]
            delta = (target - today.weekday()) % 7
            if weekday_match.group(1) and delta == 0:
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
        except ValueError as exc:
            raise GoogleIntegrationError("Use today, tomorrow, or an ISO date such as 2026-09-02.") from exc

    def _resolve_start(self, details: dict[str, Any]) -> datetime:
        time_text = str(details.get("time") or "").strip().casefold().replace(".", "")
        if not time_text:
            raise GoogleIntegrationError("Include a meeting time before approving the calendar action.")
        match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", time_text)
        if not match:
            raise GoogleIntegrationError("Use a meeting time such as 4 PM or 16:00.")
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3)
        if minute > 59 or hour > 23:
            raise GoogleIntegrationError("The meeting time is not valid.")
        if meridiem:
            if not 1 <= hour <= 12:
                raise GoogleIntegrationError("Use a 12-hour time such as 4 PM.")
            hour = hour % 12 + (12 if meridiem == "pm" else 0)
        elif hour <= 7:
            hour += 12
        meeting_date = self._resolve_date(str(details.get("date") or "today"))
        return datetime.combine(meeting_date, time(hour, minute), tzinfo=self.timezone)

    def _event_payload(self, details: dict[str, Any]) -> dict[str, Any]:
        start = self._resolve_start(details)
        duration = int(details.get("duration_minutes") or 30)
        duration = max(15, min(duration, 480))
        end = start + timedelta(minutes=duration)
        participant = str(details.get("participant") or "").strip()
        participant_email = str(details.get("participant_email") or "").strip()
        summary = str(details.get("title") or "").strip()
        if not summary:
            summary = f"Meeting with {participant}" if participant else "ElaraX meeting"
        body: dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start.isoformat(), "timeZone": self.timezone_name},
            "end": {"dateTime": end.isoformat(), "timeZone": self.timezone_name},
            "conferenceData": {
                "createRequest": {
                    "requestId": uuid4().hex,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }
        if participant_email and "@" in participant_email:
            body["attendees"] = [{"email": participant_email}]
        return body

    def find_conflicts(self, details: dict[str, Any]) -> list[dict[str, Any]]:
        start = self._resolve_start(details)
        duration = int(details.get("duration_minutes") or 30)
        end = start + timedelta(minutes=max(15, min(duration, 480)))
        try:
            response = (
                self._client()
                .freebusy()
                .query(
                    body={
                        "timeMin": start.isoformat(),
                        "timeMax": end.isoformat(),
                        "timeZone": self.timezone_name,
                        "items": [{"id": "primary"}],
                    }
                )
                .execute()
            )
            return response.get("calendars", {}).get("primary", {}).get("busy", [])
        except HttpError as exc:
            raise GoogleIntegrationError("Calendar availability could not be checked.") from exc

    def create_event(self, details: dict[str, Any]) -> dict[str, Any]:
        event_body = self._event_payload(details)
        try:
            created = (
                self._client()
                .events()
                .insert(
                    calendarId="primary",
                    body=event_body,
                    conferenceDataVersion=1,
                    sendUpdates="all" if event_body.get("attendees") else "none",
                )
                .execute()
            )
            return {"ok": True, "mock": False, "provider": "google", **self._to_event(created)}
        except HttpError as exc:
            raise GoogleIntegrationError("Google Calendar rejected the create request.") from exc

    def _find_event_id(self, details: dict[str, Any]) -> str:
        if details.get("event_id"):
            return str(details["event_id"])
        query = str(details.get("event_query") or details.get("participant") or "").strip()
        if not query:
            raise GoogleIntegrationError("Include the meeting name before approving this action.")
        matches = self.list_events(query=query, max_results=10)
        if not matches:
            raise GoogleIntegrationError(f'No upcoming calendar event matched "{query}".')
        return str(matches[0]["id"])

    def reschedule_event(self, details: dict[str, Any]) -> dict[str, Any]:
        event_id = self._find_event_id(details)
        start = self._resolve_start(details)
        duration = int(details.get("duration_minutes") or 30)
        end = start + timedelta(minutes=max(15, min(duration, 480)))
        body = {
            "start": {"dateTime": start.isoformat(), "timeZone": self.timezone_name},
            "end": {"dateTime": end.isoformat(), "timeZone": self.timezone_name},
        }
        try:
            updated = (
                self._client()
                .events()
                .patch(
                    calendarId="primary",
                    eventId=event_id,
                    body=body,
                    sendUpdates="all",
                )
                .execute()
            )
            return {"ok": True, "mock": False, "provider": "google", **self._to_event(updated)}
        except HttpError as exc:
            raise GoogleIntegrationError("Google Calendar rejected the reschedule request.") from exc

    def cancel_event(self, details: dict[str, Any]) -> dict[str, Any]:
        event_id = self._find_event_id(details)
        try:
            self._client().events().delete(
                calendarId="primary", eventId=event_id, sendUpdates="all"
            ).execute()
            return {
                "ok": True,
                "mock": False,
                "provider": "google",
                "operation": "cancel_event",
                "event_id": event_id,
            }
        except HttpError as exc:
            raise GoogleIntegrationError("Google Calendar rejected the cancellation request.") from exc
