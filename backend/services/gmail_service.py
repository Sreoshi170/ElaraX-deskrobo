"""Real Gmail API operations behind a small mockable service boundary."""

import base64
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Any, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.services.google_auth_service import (
    GoogleAuthManager,
    GoogleIntegrationError,
    google_auth_manager,
)


class GmailService:
    provider_name = "google"

    def __init__(self, auth: GoogleAuthManager = google_auth_manager) -> None:
        self.auth = auth

    def _client(self):
        return build(
            "gmail",
            "v1",
            credentials=self.auth.get_credentials(),
            cache_discovery=False,
        )

    @staticmethod
    def _headers(message: dict[str, Any]) -> dict[str, str]:
        headers = message.get("payload", {}).get("headers", [])
        return {str(header.get("name", "")).casefold(): str(header.get("value", "")) for header in headers}

    @classmethod
    def _to_email(cls, message: dict[str, Any]) -> dict[str, Any]:
        headers = cls._headers(message)
        labels = set(message.get("labelIds", []))
        sender_name, sender_email = parseaddr(headers.get("from", ""))
        _, reply_to = parseaddr(headers.get("reply-to", ""))
        return {
            "id": message["id"],
            "thread_id": message.get("threadId"),
            "sender": sender_email or headers.get("from", "Unknown sender"),
            "sender_name": sender_name or sender_email or "Unknown sender",
            "reply_to": reply_to or None,
            "subject": headers.get("subject") or "(no subject)",
            "snippet": message.get("snippet", ""),
            "date": headers.get("date"),
            "unread": "UNREAD" in labels,
            "urgent": "IMPORTANT" in labels,
            "labels": sorted(labels),
            "message_id": headers.get("message-id") or None,
            "references": headers.get("references") or None,
            "auto_submitted": headers.get("auto-submitted") or None,
            "list_unsubscribe": headers.get("list-unsubscribe") or None,
            "provider": "google",
        }

    @staticmethod
    def _decode_body(payload: dict[str, Any]) -> str:
        mime_type = payload.get("mimeType", "")
        data = payload.get("body", {}).get("data")
        if data and mime_type in {"text/plain", "text/html"}:
            try:
                return base64.urlsafe_b64decode(data.encode("ascii")).decode("utf-8", errors="replace")
            except (ValueError, UnicodeError):
                return ""
        plain_parts: list[str] = []
        html_parts: list[str] = []
        for part in payload.get("parts", []) or []:
            decoded = GmailService._decode_body(part)
            if not decoded:
                continue
            if part.get("mimeType") == "text/plain":
                plain_parts.append(decoded)
            elif part.get("mimeType") == "text/html":
                html_parts.append(decoded)
            else:
                plain_parts.append(decoded)
        return "\n".join(plain_parts or html_parts)

    def get_profile(self) -> dict[str, Any]:
        try:
            return self._client().users().getProfile(userId="me").execute()
        except HttpError as exc:
            raise GoogleIntegrationError("Gmail account details could not be loaded.") from exc

    def list_emails(
        self,
        *,
        max_results: int = 10,
        unread_only: bool = False,
        important_only: bool = False,
        query: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        query_parts = ["newer_than:90d"]
        if unread_only:
            query_parts.append("is:unread")
        if important_only:
            query_parts.append("is:important")
        if query:
            query_parts.append(query)
        try:
            client = self._client()
            listing = (
                client.users()
                .messages()
                .list(userId="me", q=" ".join(query_parts), maxResults=max(1, min(max_results, 25)))
                .execute()
            )
            emails: list[dict[str, Any]] = []
            for reference in listing.get("messages", []):
                message = (
                    client.users()
                    .messages()
                    .get(
                        userId="me",
                        id=reference["id"],
                        format="metadata",
                        metadataHeaders=[
                            "From",
                            "To",
                            "Reply-To",
                            "Subject",
                            "Date",
                            "Message-ID",
                            "References",
                            "Auto-Submitted",
                            "List-Unsubscribe",
                        ],
                    )
                    .execute()
                )
                emails.append(self._to_email(message))
            return emails
        except HttpError as exc:
            raise GoogleIntegrationError(
                "Gmail could not be read. Check that the Gmail API is enabled and reconnect Google."
            ) from exc

    def get_email(self, message_id: str) -> dict[str, Any]:
        try:
            message = (
                self._client().users().messages().get(userId="me", id=message_id, format="full").execute()
            )
        except HttpError as exc:
            raise GoogleIntegrationError("That Gmail message could not be loaded.") from exc
        result = self._to_email(message)
        result["body"] = self._decode_body(message.get("payload", {}))
        return result

    def send_reply(self, payload: dict[str, Any]) -> dict[str, Any]:
        recipient = str(payload.get("recipient") or "").strip()
        subject = str(payload.get("subject") or "").strip()
        body = str(payload.get("draft") or payload.get("body") or "").strip()
        if not recipient or "@" not in recipient:
            raise GoogleIntegrationError("A valid recipient email address is required before sending.")
        if not body:
            raise GoogleIntegrationError("The reply is empty and was not sent.")

        message = EmailMessage()
        message["To"] = recipient
        message["Subject"] = subject or "Re: Your message"
        in_reply_to = str(payload.get("in_reply_to") or "").replace("\r", " ").replace("\n", " ").strip()
        references = str(payload.get("references") or "").replace("\r", " ").replace("\n", " ").strip()
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
        if references:
            message["References"] = references
        message.set_content(body)
        request_body: dict[str, Any] = {
            "raw": base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        }
        thread_id = payload.get("thread_id")
        if thread_id:
            request_body["threadId"] = thread_id
        try:
            sent = self._client().users().messages().send(userId="me", body=request_body).execute()
        except HttpError as exc:
            raise GoogleIntegrationError("Gmail rejected the send request. No success was reported.") from exc
        return {
            "ok": True,
            "mock": False,
            "provider": "google",
            "operation": "send_reply",
            "message_id": sent.get("id"),
            "thread_id": sent.get("threadId"),
        }

    def send_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a confirmed new message using the same MIME-safe Gmail boundary."""

        result = self.send_reply(payload)
        result["operation"] = "send_email"
        return result

    def forward_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Forward the selected message as a new plain-text Gmail message."""

        recipient = str(payload.get("recipient") or "").strip()
        source_email_id = str(payload.get("email_id") or "").strip()
        source_type = str(payload.get("source_type") or "email")
        if not recipient or "@" not in recipient:
            raise GoogleIntegrationError("A valid recipient email address is required before forwarding.")
        if not source_email_id and source_type != "calendar":
            raise GoogleIntegrationError("Select an email to forward before sending.")
        source = self.get_email(source_email_id) if source_email_id else {}
        if source_email_id and not source:
            raise GoogleIntegrationError("The email selected for forwarding could not be loaded.")

        subject = str(payload.get("subject") or f"Fwd: {source.get('subject') or 'Your message'}").strip()
        body = str(payload.get("draft") or "").strip()
        if not body:
            raise GoogleIntegrationError("The forwarded email is empty and was not sent.")
        message = EmailMessage()
        message["To"] = recipient
        message["Subject"] = subject or "Fwd: Your message"
        message.set_content(body)
        request_body: dict[str, Any] = {
            "raw": base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        }
        try:
            sent = self._client().users().messages().send(userId="me", body=request_body).execute()
        except HttpError as exc:
            raise GoogleIntegrationError("Gmail rejected the forward request. No success was reported.") from exc
        return {
            "ok": True,
            "mock": False,
            "provider": "google",
            "operation": "forward_email",
            "message_id": sent.get("id"),
            "thread_id": sent.get("threadId"),
        }

    def _modify_labels(
        self,
        payload: dict[str, Any],
        *,
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
        operation: str,
    ) -> dict[str, Any]:
        message_id = str(payload.get("email_id") or "").strip()
        if not message_id:
            raise GoogleIntegrationError("Select an email before applying that change.")
        try:
            self._client().users().messages().modify(
                userId="me",
                id=message_id,
                body={
                    "addLabelIds": add_label_ids or [],
                    "removeLabelIds": remove_label_ids or [],
                },
            ).execute()
        except HttpError as exc:
            raise GoogleIntegrationError("Gmail rejected the email change.") from exc
        return {
            "ok": True,
            "mock": False,
            "provider": "google",
            "operation": operation,
            "email_id": message_id,
        }

    def mark_read(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._modify_labels(payload, remove_label_ids=["UNREAD"], operation="mark_read")

    def mark_unread(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._modify_labels(payload, add_label_ids=["UNREAD"], operation="mark_unread")

    def star_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._modify_labels(payload, add_label_ids=["STARRED"], operation="star_email")

    def unstar_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._modify_labels(payload, remove_label_ids=["STARRED"], operation="unstar_email")

    def archive_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._modify_labels(payload, remove_label_ids=["INBOX"], operation="archive_email")

    def trash_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        message_id = str(payload.get("email_id") or "").strip()
        if not message_id:
            raise GoogleIntegrationError("Select an email before moving it to trash.")
        try:
            self._client().users().messages().trash(userId="me", id=message_id).execute()
        except HttpError as exc:
            raise GoogleIntegrationError("Gmail rejected the move to trash.") from exc
        return {
            "ok": True,
            "mock": False,
            "provider": "google",
            "operation": "trash_email",
            "email_id": message_id,
        }

    def delete_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        message_id = str(payload.get("email_id") or "").strip()
        if not message_id:
            raise GoogleIntegrationError("Select an email before permanently deleting it.")
        try:
            self._client().users().messages().delete(userId="me", id=message_id).execute()
        except HttpError as exc:
            raise GoogleIntegrationError("Gmail rejected the permanent delete.") from exc
        return {
            "ok": True,
            "mock": False,
            "provider": "google",
            "operation": "delete_email",
            "email_id": message_id,
        }
