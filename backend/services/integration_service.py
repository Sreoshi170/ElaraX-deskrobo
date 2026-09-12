"""Select real Google services only after the local account is connected."""

from typing import Any, Optional

from backend.services.gmail_service import GmailService
from backend.services.google_auth_service import google_auth_manager
from backend.services.google_calendar_service import GoogleCalendarService
from backend.services.mock_calendar_service import find_available_slots as find_mock_available_slots
from backend.services.mock_calendar_service import list_events as list_mock_events
from backend.services.mock_email_service import list_emails as list_mock_emails
from backend.services.mock_email_service import mock_send_reply


class MockEmailService:
    provider_name = "mock"

    def get_profile(self) -> dict[str, Any]:
        return {"emailAddress": None}

    def list_emails(
        self,
        *,
        max_results: int = 10,
        unread_only: bool = False,
        important_only: bool = False,
        query: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        emails = list_mock_emails()
        if unread_only:
            emails = [email for email in emails if email["unread"]]
        if important_only:
            emails = [email for email in emails if email["urgent"]]
        if query:
            lowered = query.casefold()
            emails = [
                email
                for email in emails
                if lowered in f"{email['sender']} {email['subject']} {email['snippet']}".casefold()
            ]
        return emails[:max_results]

    def get_email(self, message_id: str) -> dict[str, Any]:
        for email in list_mock_emails():
            if email["id"] == message_id:
                return {**email, "body": email["snippet"], "provider": "mock"}
        return {}

    def send_reply(self, payload: dict[str, Any]) -> dict[str, Any]:
        return mock_send_reply(payload)

    def send_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = mock_send_reply(payload)
        result["operation"] = "send_email"
        return result

    def forward_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = mock_send_reply(payload)
        result["operation"] = "forward_email"
        return result

    def mark_read(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "mock": True, "operation": "mark_read", "email_id": payload.get("email_id")}

    def mark_unread(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "mock": True, "operation": "mark_unread", "email_id": payload.get("email_id")}

    def star_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "mock": True, "operation": "star_email", "email_id": payload.get("email_id")}

    def unstar_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "mock": True, "operation": "unstar_email", "email_id": payload.get("email_id")}

    def archive_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "mock": True, "operation": "archive_email", "email_id": payload.get("email_id")}

    def trash_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "mock": True, "operation": "trash_email", "email_id": payload.get("email_id")}

    def delete_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "mock": True, "operation": "delete_email", "email_id": payload.get("email_id")}


class MockCalendarService:
    provider_name = "mock"

    def list_events(
        self,
        day: Optional[str] = None,
        *,
        max_results: int = 20,
        query: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        events = list_mock_events(day)
        if query:
            events = [event for event in events if query.casefold() in event["title"].casefold()]
        return events[:max_results]

    def find_conflicts(self, details: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    def find_available_slots(
        self,
        before_date: str,
        duration_minutes: int = 30,
        working_hours: tuple[int, int] = (9, 18),
    ) -> list[dict[str, Any]]:
        return find_mock_available_slots(before_date, duration_minutes, working_hours)


def google_is_connected() -> bool:
    return bool(google_auth_manager.connection_summary().get("connected"))


def get_email_service():
    return GmailService() if google_is_connected() else MockEmailService()


def get_calendar_service():
    return GoogleCalendarService() if google_is_connected() else MockCalendarService()
