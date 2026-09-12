"""HTTP boundary tests for ElaraX."""

import base64

from fastapi.testclient import TestClient

import backend.api as api_module
from backend.api import app


client = TestClient(app)


def test_health_and_overview() -> None:
    health = client.get("/api/health")
    overview = client.get("/api/overview")

    assert health.status_code == 200
    assert health.json()["graph"] == "ready"
    assert len(overview.json()["urgent_emails"]) == 1
    assert overview.json()["robot"]["mode"] == "simulation"


def test_chat_routes_to_graph() -> None:
    response = client.post("/api/chat", json={"message": "What important emails do I have?"})

    assert response.status_code == 200
    assert response.json()["intent"] == "GET_URGENT_EMAILS"
    assert "1 important email" in response.json()["response"]
    assert response.json()["agent_mode"] == "deterministic"
    assert response.json()["task_results"][0]["intent"] == "GET_URGENT_EMAILS"
    assert response.json()["emails"][0]["subject"] == "Launch review"
    assert response.json()["emails"][0]["urgent"] is True


def test_consequential_action_requires_confirmation() -> None:
    chat_response = client.post(
        "/api/chat",
        json={"message": "Schedule meeting with Rahul tomorrow at 4", "thread_id": "api-confirm"},
    )

    assert chat_response.json()["requires_confirmation"] is True
    assert chat_response.json()["pending_action"]["action"] == "CREATE_MEETING"

    confirm_response = client.post(
        "/api/confirm", json={"thread_id": "api-confirm", "decision": "approve"}
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["decision"] == "approved"
    assert confirm_response.json()["result"]["mock"] is True


def test_deadline_meeting_confirmation_books_then_sends_one_threaded_reply(monkeypatch) -> None:
    thread_id = "api-deadline-auto-reply"
    pending = {
        "action": "CREATE_MEETING",
        "details": {
            "participant_name": "Alice",
            "participant_email": "alice@example.com",
            "date": "tomorrow",
            "time": "2 pm",
            "title": "SIS discussion",
            "source_email_id": "email-001",
            "source_thread_id": "thread-001",
            "source_message_id": "<message-001@example.com>",
            "source_references": "<root@example.com>",
            "source_subject": "SIS discussion",
            "auto_reply_with_link": True,
        },
    }
    api_module._pending_actions[thread_id] = pending
    calendar_calls: list[dict] = []
    reply_calls: list[dict] = []

    class FakeCalendarService:
        provider_name = "google"

        def create_event(self, details):
            calendar_calls.append(details)
            return {
                "ok": True,
                "id": "event-001",
                "meet_link": "https://meet.google.com/sis-demo",
            }

    class FakeEmailService:
        provider_name = "google"

        def get_email(self, message_id):
            assert message_id == "email-001"
            return {
                "id": "email-001",
                "sender": "alice@example.com",
                "reply_to": None,
            }

        def send_reply(self, payload):
            reply_calls.append(payload)
            return {"ok": True, "operation": "send_reply", "message_id": "reply-001"}

    monkeypatch.setattr(api_module.integration_service, "get_calendar_service", lambda: FakeCalendarService())
    monkeypatch.setattr(api_module.integration_service, "get_email_service", lambda: FakeEmailService())

    response = client.post("/api/confirm", json={"thread_id": thread_id, "decision": "approve"})

    assert response.status_code == 200
    assert len(calendar_calls) == 1
    assert len(reply_calls) == 1
    assert reply_calls[0]["thread_id"] == "thread-001"
    assert reply_calls[0]["in_reply_to"] == "<message-001@example.com>"
    assert reply_calls[0]["references"] == "<root@example.com>"
    assert "https://meet.google.com/sis-demo" in reply_calls[0]["draft"]
    assert response.json()["result"]["calendar"]["id"] == "event-001"
    assert response.json()["result"]["email"]["message_id"] == "reply-001"


def test_deadline_meeting_failure_does_not_send_reply(monkeypatch) -> None:
    thread_id = "api-deadline-no-reply-on-failure"
    api_module._pending_actions[thread_id] = {
        "action": "CREATE_MEETING",
        "details": {
            "participant_email": "alice@example.com",
            "auto_reply_with_link": True,
        },
    }
    replies: list[dict] = []

    class FailingCalendarService:
        provider_name = "google"

        def create_event(self, details):
            from backend.services.google_auth_service import GoogleIntegrationError

            raise GoogleIntegrationError("calendar unavailable")

    class FakeEmailService:
        provider_name = "google"

        def get_email(self, message_id):
            return {"id": message_id, "sender": "alice@example.com"}

        def send_reply(self, payload):
            replies.append(payload)
            return {"ok": True}

    monkeypatch.setattr(api_module.integration_service, "get_calendar_service", lambda: FailingCalendarService())
    monkeypatch.setattr(api_module.integration_service, "get_email_service", lambda: FakeEmailService())

    response = client.post("/api/confirm", json={"thread_id": thread_id, "decision": "approve"})

    assert response.status_code == 409
    assert replies == []


def test_deadline_auto_reply_refuses_recipient_not_found_in_source_email(monkeypatch) -> None:
    thread_id = "api-deadline-recipient-mismatch"
    api_module._pending_actions[thread_id] = {
        "action": "CREATE_MEETING",
        "details": {
            "participant_email": "guessed@example.com",
            "source_email_id": "email-001",
            "auto_reply_with_link": True,
        },
    }
    replies: list[dict] = []
    calendar_calls: list[dict] = []

    class FakeCalendarService:
        provider_name = "google"

        def create_event(self, details):
            calendar_calls.append(details)
            return {"ok": True, "id": "event-001", "meet_link": "https://meet.google.com/sis-demo"}

    class FakeEmailService:
        provider_name = "google"

        def get_email(self, message_id):
            return {"id": message_id, "sender": "alice@example.com"}

        def send_reply(self, payload):
            replies.append(payload)
            return {"ok": True}

    monkeypatch.setattr(api_module.integration_service, "get_calendar_service", lambda: FakeCalendarService())
    monkeypatch.setattr(api_module.integration_service, "get_email_service", lambda: FakeEmailService())

    response = client.post("/api/confirm", json={"thread_id": thread_id, "decision": "approve"})

    assert response.status_code == 409
    assert replies == []
    assert calendar_calls == []


def test_new_email_send_requires_confirmation_then_uses_email_service() -> None:
    thread_id = "api-send-new-email"
    chat_response = client.post(
        "/api/chat",
        json={
            "message": 'send email to alice@example.com "hello there"',
            "thread_id": thread_id,
        },
    )

    assert chat_response.status_code == 200
    assert chat_response.json()["intent"] == "SEND_EMAIL"
    assert chat_response.json()["pending_action"]["recipient"] == "alice@example.com"
    assert chat_response.json()["requires_confirmation"] is True

    confirm_response = client.post(
        "/api/confirm", json={"thread_id": thread_id, "decision": "approve"}
    )

    assert confirm_response.status_code == 200
    assert confirm_response.json()["result"]["operation"] == "send_email"


def test_recipient_correction_updates_pending_action_without_replanning() -> None:
    thread_id = "api-recipient-correction"
    api_module._pending_actions[thread_id] = {
        "action": "SEND_EMAIL",
        "recipient": "wrong@example.com",
        "subject": "Status",
        "draft": "Hello",
    }

    response = client.post(
        "/api/chat",
        json={
            "thread_id": thread_id,
            "message": "That email is wrong, use corrected@example.com instead.",
        },
    )

    assert response.status_code == 200
    assert response.json()["pending_action"]["recipient"] == "corrected@example.com"
    assert response.json()["requires_confirmation"] is True
    assert "Updated the pending recipient" in response.json()["response"]


def test_google_launch_requires_local_header() -> None:
    response = client.post("/api/v1/auth/google/launch")

    assert response.status_code == 403


def test_google_launch_uses_system_browser(monkeypatch) -> None:
    monkeypatch.setattr(
        api_module.google_auth_manager,
        "begin_authorization",
        lambda: "https://accounts.google.com/o/oauth2/auth?state=test",
    )
    opened: list[str] = []
    monkeypatch.setattr(
        api_module.webbrowser,
        "open_new_tab",
        lambda url: opened.append(url) or True,
    )

    response = client.post(
        "/api/v1/auth/google/launch",
        headers={"X-ElaraX-Local": "1"},
    )

    assert response.status_code == 200
    assert response.json() == {"launched": True}
    assert opened == ["https://accounts.google.com/o/oauth2/auth?state=test"]


def test_voice_transcription_accepts_short_audio(monkeypatch) -> None:
    monkeypatch.setattr(
        api_module.voice_transcription_service,
        "transcribe_audio",
        lambda audio_bytes, mime_type: "Show my important emails",
    )

    response = client.post(
        "/api/voice/transcribe",
        json={
            "audio_base64": base64.b64encode(b"short fake webm audio").decode("ascii"),
            "mime_type": "audio/webm;codecs=opus",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"transcript": "Show my important emails"}


def test_voice_transcription_rejects_unsupported_media() -> None:
    response = client.post(
        "/api/voice/transcribe",
        json={
            "audio_base64": base64.b64encode(b"not audio").decode("ascii"),
            "mime_type": "video/webm",
        },
    )

    assert response.status_code == 415


def test_voice_transcription_reports_provider_unavailability(monkeypatch) -> None:
    monkeypatch.setattr(
        api_module.voice_transcription_service,
        "transcribe_audio",
        lambda audio_bytes, mime_type: None,
    )
    monkeypatch.setattr(
        api_module.voice_transcription_service,
        "last_error",
        "TranscriptionUnavailable: primary: ClientError; fallback: ReadTimeout",
    )

    response = client.post(
        "/api/voice/transcribe",
        json={
            "audio_base64": base64.b64encode(b"valid but unavailable audio").decode("ascii"),
            "mime_type": "audio/webm",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Voice transcription is temporarily unavailable. Please try again in a moment."
    )


def test_voice_synthesis_returns_wav(monkeypatch) -> None:
    wav_bytes = b"RIFF\x00\x00\x00\x00WAVEfmt "
    monkeypatch.setattr(
        api_module.gemini_reasoning_service,
        "synthesize_speech",
        lambda text: wav_bytes if text == "ElaraX is ready." else None,
    )

    response = client.post(
        "/api/voice/synthesize",
        json={"text": "ElaraX is ready."},
    )

    assert response.status_code == 200
    assert response.json()["mime_type"] == "audio/wav"
    assert base64.b64decode(response.json()["audio_base64"]) == wav_bytes


def test_voice_synthesis_falls_back_to_edge_tts_with_requested_language(monkeypatch) -> None:
    edge_bytes = b"ID3 edge audio"
    calls: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        api_module.gemini_reasoning_service,
        "synthesize_speech",
        lambda text: None,
    )

    def synthesize_with_edge(text: str, language: str | None = None) -> bytes:
        calls.append((text, language))
        return edge_bytes

    monkeypatch.setattr(
        api_module.edge_tts_service,
        "synthesize_speech",
        synthesize_with_edge,
    )

    response = client.post(
        "/api/voice/synthesize",
        json={"text": "amar important email bolo", "language": "bn"},
    )

    assert response.status_code == 200
    assert response.json()["mime_type"] == "audio/mpeg"
    assert base64.b64decode(response.json()["audio_base64"]) == edge_bytes
    assert calls == [("amar important email bolo", "bn")]


def test_voice_synthesis_reports_unavailable_when_both_providers_fail(monkeypatch) -> None:
    monkeypatch.setattr(
        api_module.gemini_reasoning_service,
        "synthesize_speech",
        lambda text: None,
    )
    monkeypatch.setattr(
        api_module.edge_tts_service,
        "synthesize_speech",
        lambda text, language=None: None,
    )

    response = client.post("/api/voice/synthesize", json={"text": "ElaraX is ready."})

    assert response.status_code == 503
    assert response.json()["detail"] == "Spoken output is temporarily unavailable."


def test_confirmed_calendar_event_can_be_forwarded_from_same_thread(monkeypatch) -> None:
    thread_id = "api-forward-created-meeting"

    class FakeCalendarService:
        provider_name = "google"

        def list_events(self, day=None, *, max_results=20, query=None):
            return []

        def find_conflicts(self, details):
            return []

        def create_event(self, details):
            return {
                "id": "created-event",
                "title": "SIS account discussion",
                "time": "11:00 AM",
                "meet_link": "https://meet.google.com/abc-defg-hij",
            }

    class FakeEmailService:
        provider_name = "google"

        def forward_email(self, payload):
            return {"ok": True, "mock": False, "operation": "forward_email", "email_id": None}

        def get_email(self, message_id):
            return {}

        def list_emails(self, **kwargs):
            return []

    monkeypatch.setattr(
        api_module.integration_service,
        "get_calendar_service",
        lambda: FakeCalendarService(),
    )

    prepared = client.post(
        "/api/chat",
        json={"thread_id": thread_id, "message": "Book a Google Meet at 11 am."},
    )
    assert prepared.status_code == 200
    assert prepared.json()["pending_action"]["action"] == "CREATE_MEETING"

    confirmed = client.post(
        "/api/confirm",
        json={"thread_id": thread_id, "decision": "approve"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["result"]["id"] == "created-event"

    monkeypatch.setattr(
        api_module.integration_service,
        "get_email_service",
        lambda: FakeEmailService(),
    )
    forward = client.post(
        "/api/chat",
        json={
            "thread_id": thread_id,
            "message": "Forward the meeting link that you created to lokeshhajraiem28@gmail.com.",
        },
    )

    assert forward.status_code == 200
    assert forward.json()["intent"] == "FORWARD_EMAIL"
    assert forward.json()["pending_action"]["source_type"] == "calendar"
    assert "https://meet.google.com/abc-defg-hij" in forward.json()["pending_action"]["draft"]

    forwarded = client.post(
        "/api/confirm",
        json={"thread_id": thread_id, "decision": "approve"},
    )
    assert forwarded.status_code == 200
    assert forwarded.json()["result"]["operation"] == "forward_email"


def test_invoice_automation_status_and_update(monkeypatch) -> None:
    status = {
        "enabled": False,
        "connected": True,
        "poll_interval_seconds": 300,
        "reply_template": "Safe acknowledgement",
        "total_replies_sent": 0,
        "last_run_at": None,
        "last_error": None,
        "recent_replies": [],
    }
    monkeypatch.setattr(api_module.invoice_automation_service, "status", lambda: status)
    monkeypatch.setattr(
        api_module.invoice_automation_service,
        "set_enabled",
        lambda enabled: {**status, "enabled": enabled},
    )
    woke: list[bool] = []
    monkeypatch.setattr(api_module.invoice_automation_worker, "wake", lambda: woke.append(True))

    current = client.get("/api/automation/invoice")
    updated = client.put("/api/automation/invoice", json={"enabled": True})

    assert current.status_code == 200
    assert current.json()["enabled"] is False
    assert updated.status_code == 200
    assert updated.json()["enabled"] is True
    assert woke == [True]


def test_action_item_endpoints_list_open_items_and_complete_them(monkeypatch) -> None:
    item = {
        "id": "action-1",
        "description": "Send the invoice",
        "due_date": "Friday",
        "source_email_id": "email-1",
        "source_subject": "Invoice",
        "status": "open",
        "created_at": "2026-09-06T00:00:00+00:00",
    }
    monkeypatch.setattr(
        api_module.action_item_service,
        "list_items",
        lambda status=None: [item] if status == "open" else [],
    )
    monkeypatch.setattr(
        api_module.action_item_service,
        "complete_item",
        lambda item_id: {**item, "status": "done"},
    )

    listed = client.get("/api/action-items?status=open")
    completed = client.post("/api/action-items/action-1/complete")

    assert listed.status_code == 200
    assert listed.json()["items"][0]["description"] == "Send the invoice"
    assert completed.status_code == 200
    assert completed.json()["item"]["status"] == "done"
