"""A narrowly scoped, locally persisted invoice acknowledgement automation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, RLock, Thread
from typing import Any, Callable, Optional

from backend.config import (
    INVOICE_AUTOMATION_INTERVAL_SECONDS,
    INVOICE_AUTOMATION_SETTINGS_FILE,
    INVOICE_AUTOMATION_MAX_REPLIES_PER_RUN,
)
from backend.services import integration_service
from backend.services.google_auth_service import GoogleIntegrationError


DEFAULT_INVOICE_REPLY = (
    "Thank you for sending your invoice. This is an acknowledgement of receipt only. "
    "We will review it and contact you if any further information is needed."
)
_NO_REPLY_MARKERS = ("no-reply", "noreply", "do-not-reply", "donotreply")
_EXCLUDED_INVOICE_MARKERS = ("past due", "overdue", "payment reminder", "final notice")


class InvoiceAutomationService:
    """Send one safe receipt acknowledgement for new unread invoice threads.

    This intentionally does not use a language model. The reply body is fixed,
    it does not acknowledge payment or approve a charge, and each Gmail thread
    is persisted as processed only after Gmail accepts the reply.
    """

    def __init__(
        self,
        *,
        settings_file: Path = INVOICE_AUTOMATION_SETTINGS_FILE,
        email_service_factory: Callable[[], Any] = integration_service.get_email_service,
        google_connected: Callable[[], bool] = integration_service.google_is_connected,
        poll_interval_seconds: int = INVOICE_AUTOMATION_INTERVAL_SECONDS,
        max_replies_per_run: int = INVOICE_AUTOMATION_MAX_REPLIES_PER_RUN,
    ) -> None:
        self.settings_file = settings_file
        self.email_service_factory = email_service_factory
        self.google_connected = google_connected
        self.poll_interval_seconds = max(60, int(poll_interval_seconds))
        self.max_replies_per_run = max(1, min(int(max_replies_per_run), 10))
        self._lock = RLock()

    @staticmethod
    def _default_settings() -> dict[str, Any]:
        return {
            "enabled": False,
            "reply_template": DEFAULT_INVOICE_REPLY,
            "processed_thread_ids": [],
            "recent_replies": [],
            "total_replies_sent": 0,
            "last_run_at": None,
            "last_error": None,
        }

    def _load_locked(self) -> dict[str, Any]:
        data = self._default_settings()
        try:
            loaded = json.loads(self.settings_file.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return data
        if not isinstance(loaded, dict):
            return data
        data["enabled"] = bool(loaded.get("enabled"))
        data["reply_template"] = DEFAULT_INVOICE_REPLY
        data["processed_thread_ids"] = [
            str(value) for value in loaded.get("processed_thread_ids", []) if str(value).strip()
        ][-1_000:]
        data["recent_replies"] = [
            item for item in loaded.get("recent_replies", []) if isinstance(item, dict)
        ][-12:]
        data["total_replies_sent"] = max(0, int(loaded.get("total_replies_sent", 0) or 0))
        data["last_run_at"] = loaded.get("last_run_at") or None
        data["last_error"] = loaded.get("last_error") or None
        return data

    def _save_locked(self, data: dict[str, Any]) -> None:
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = self.settings_file.with_suffix(".tmp")
        temporary_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temporary_file.replace(self.settings_file)

    def _public_status(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "enabled": bool(data["enabled"]),
            "connected": bool(self.google_connected()),
            "poll_interval_seconds": self.poll_interval_seconds,
            "reply_template": DEFAULT_INVOICE_REPLY,
            "total_replies_sent": int(data["total_replies_sent"]),
            "last_run_at": data["last_run_at"],
            "last_error": data["last_error"],
            "recent_replies": list(data["recent_replies"]),
        }

    def status(self) -> dict[str, Any]:
        with self._lock:
            return self._public_status(self._load_locked())

    def set_enabled(self, enabled: bool) -> dict[str, Any]:
        if enabled and not self.google_connected():
            raise GoogleIntegrationError("Connect your Google account before enabling invoice auto-replies.")
        with self._lock:
            data = self._load_locked()
            data["enabled"] = enabled
            data["last_error"] = None
            self._save_locked(data)
            return self._public_status(data)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _is_invoice(email: dict[str, Any]) -> bool:
        combined = " ".join(
            str(email.get(field) or "") for field in ("subject", "snippet", "body")
        ).casefold()
        return "invoice" in combined and not any(marker in combined for marker in _EXCLUDED_INVOICE_MARKERS)

    @staticmethod
    def _is_automated_or_no_reply(email: dict[str, Any], recipient: str) -> bool:
        address = recipient.casefold()
        if any(marker in address for marker in _NO_REPLY_MARKERS):
            return True
        return bool(email.get("list_unsubscribe") or email.get("auto_submitted"))

    @staticmethod
    def _reply_subject(subject: str) -> str:
        cleaned = " ".join(subject.split())[:250] or "Your invoice"
        return cleaned if cleaned.casefold().startswith("re:") else f"Re: {cleaned}"

    def run_once(self) -> dict[str, Any]:
        """Check Gmail once. Every external send remains constrained to this method."""

        with self._lock:
            data = self._load_locked()
            if not data["enabled"]:
                return self._public_status(data)
            if not self.google_connected():
                data["last_run_at"] = self._now()
                data["last_error"] = "Google is not connected. Invoice auto-replies are paused."
                self._save_locked(data)
                return self._public_status(data)

            try:
                service = self.email_service_factory()
                if getattr(service, "provider_name", "mock") != "google":
                    raise GoogleIntegrationError("A live Gmail connection is required for invoice auto-replies.")
                owner_email = str(service.get_profile().get("emailAddress") or "").casefold()
                candidates = service.list_emails(
                    max_results=25,
                    unread_only=True,
                    query="newer_than:14d invoice",
                )
                processed_threads = set(data["processed_thread_ids"])
                replies_sent = 0

                for candidate in candidates:
                    if replies_sent >= self.max_replies_per_run:
                        break
                    message_id = str(candidate.get("id") or "")
                    if not message_id:
                        continue
                    email = service.get_email(message_id)
                    thread_id = str(email.get("thread_id") or candidate.get("thread_id") or "")
                    if not thread_id or thread_id in processed_threads or not self._is_invoice(email):
                        continue
                    recipient = str(email.get("reply_to") or email.get("sender") or "").strip()
                    if not recipient or (owner_email and recipient.casefold() == owner_email):
                        continue
                    if self._is_automated_or_no_reply(email, recipient):
                        continue

                    service.send_reply(
                        {
                            "recipient": recipient,
                            "subject": self._reply_subject(str(email.get("subject") or "")),
                            "draft": DEFAULT_INVOICE_REPLY,
                            "thread_id": thread_id,
                            "in_reply_to": email.get("message_id"),
                            "references": email.get("references"),
                        }
                    )
                    processed_threads.add(thread_id)
                    data["processed_thread_ids"] = list(processed_threads)[-1_000:]
                    data["total_replies_sent"] += 1
                    data["recent_replies"] = [
                        {
                            "thread_id": thread_id,
                            "recipient": recipient,
                            "subject": self._reply_subject(str(email.get("subject") or "")),
                            "sent_at": self._now(),
                        },
                        *data["recent_replies"],
                    ][:12]
                    replies_sent += 1

                data["last_run_at"] = self._now()
                data["last_error"] = None
            except GoogleIntegrationError as exc:
                data["last_run_at"] = self._now()
                data["last_error"] = str(exc)
            except Exception:  # pragma: no cover - provider boundary; keep the worker alive
                data["last_run_at"] = self._now()
                data["last_error"] = "Invoice auto-replies could not check Gmail. They will retry later."

            self._save_locked(data)
            return self._public_status(data)


class InvoiceAutomationWorker:
    """Small local worker; it never starts in the test environment."""

    def __init__(self, service: InvoiceAutomationService) -> None:
        self.service = service
        self._stop = Event()
        self._wake = Event()
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._work, name="aetherbot-invoice-auto-reply", daemon=True)
        self._thread.start()

    def wake(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._thread = None

    def _work(self) -> None:
        while not self._stop.is_set():
            self.service.run_once()
            self._wake.wait(self.service.poll_interval_seconds)
            self._wake.clear()


invoice_automation_service = InvoiceAutomationService()
invoice_automation_worker = InvoiceAutomationWorker(invoice_automation_service)
