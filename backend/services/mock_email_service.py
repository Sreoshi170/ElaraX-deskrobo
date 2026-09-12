"""Deterministic email fixtures used until a real provider is integrated."""

from typing import Any


_EMAILS: tuple[dict[str, Any], ...] = (
    {
        "id": "email-001",
        "thread_id": "thread-001",
        "sender": "alice@example.com",
        "subject": "Launch review",
        "snippet": "Please review the launch checklist before 3 PM.",
        "unread": True,
        "urgent": True,
    },
    {
        "id": "email-002",
        "thread_id": "thread-002",
        "sender": "newsletter@example.com",
        "subject": "Weekly product digest",
        "snippet": "This week's product and engineering news.",
        "unread": True,
        "urgent": False,
    },
)


def list_emails() -> list[dict[str, Any]]:
    """Return copies so graph nodes cannot mutate shared fixtures."""

    return [dict(email) for email in _EMAILS]


def mock_send_reply(payload: dict[str, Any]) -> dict[str, Any]:
    """Represent a provider call without sending real email."""

    return {"ok": True, "mock": True, "operation": "send_reply", "payload": dict(payload)}

