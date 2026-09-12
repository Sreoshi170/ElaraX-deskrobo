"""Tests for narrowly scoped invoice acknowledgement automation."""

from pathlib import Path

import pytest

from backend.services.google_auth_service import GoogleIntegrationError
from backend.services.invoice_automation_service import (
    DEFAULT_INVOICE_REPLY,
    InvoiceAutomationService,
)


class FakeGmailService:
    provider_name = "google"

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []
        self.list_calls = 0

    def get_profile(self) -> dict[str, str]:
        return {"emailAddress": "owner@example.com"}

    def list_emails(self, **_: object) -> list[dict[str, str]]:
        self.list_calls += 1
        return [
            {"id": "invoice-1", "thread_id": "thread-invoice"},
            {"id": "no-reply-invoice", "thread_id": "thread-no-reply"},
            {"id": "overdue-invoice", "thread_id": "thread-overdue"},
        ]

    def get_email(self, message_id: str) -> dict[str, str]:
        messages = {
            "invoice-1": {
                "id": "invoice-1",
                "thread_id": "thread-invoice",
                "sender": "billing@vendor.example",
                "subject": "Invoice INV-204",
                "snippet": "Your invoice is attached.",
                "body": "Invoice INV-204",
                "message_id": "<invoice-1@example>",
                "references": "<root@example>",
            },
            "no-reply-invoice": {
                "id": "no-reply-invoice",
                "thread_id": "thread-no-reply",
                "sender": "no-reply@vendor.example",
                "subject": "Invoice available",
                "body": "Invoice ready",
            },
            "overdue-invoice": {
                "id": "overdue-invoice",
                "thread_id": "thread-overdue",
                "sender": "billing@vendor.example",
                "subject": "Past due invoice reminder",
                "body": "Your invoice is past due",
            },
        }
        return messages[message_id]

    def send_reply(self, payload: dict[str, str]) -> dict[str, str]:
        self.sent.append(payload)
        return {"ok": "true"}


def build_service(tmp_path: Path, gmail: FakeGmailService, *, connected: bool = True) -> InvoiceAutomationService:
    return InvoiceAutomationService(
        settings_file=tmp_path / "invoice-automation.json",
        email_service_factory=lambda: gmail,
        google_connected=lambda: connected,
        poll_interval_seconds=60,
        max_replies_per_run=3,
    )


def test_invoice_automation_sends_one_receipt_and_never_replies_twice(tmp_path: Path) -> None:
    gmail = FakeGmailService()
    service = build_service(tmp_path, gmail)
    service.set_enabled(True)

    first = service.run_once()
    second = service.run_once()

    assert first["enabled"] is True
    assert first["total_replies_sent"] == 1
    assert second["total_replies_sent"] == 1
    assert len(gmail.sent) == 1
    assert gmail.sent[0]["recipient"] == "billing@vendor.example"
    assert gmail.sent[0]["subject"] == "Re: Invoice INV-204"
    assert gmail.sent[0]["draft"] == DEFAULT_INVOICE_REPLY
    assert gmail.sent[0]["thread_id"] == "thread-invoice"
    assert gmail.sent[0]["in_reply_to"] == "<invoice-1@example>"


def test_invoice_automation_is_inert_until_enabled(tmp_path: Path) -> None:
    gmail = FakeGmailService()
    service = build_service(tmp_path, gmail)

    status = service.run_once()

    assert status["enabled"] is False
    assert gmail.list_calls == 0
    assert gmail.sent == []


def test_enabling_invoice_automation_requires_google_connection(tmp_path: Path) -> None:
    service = build_service(tmp_path, FakeGmailService(), connected=False)

    with pytest.raises(GoogleIntegrationError, match="Connect your Google account"):
        service.set_enabled(True)
