"""Tests for the non-executing Gemini reasoning boundary."""

from types import SimpleNamespace

from backend.services.gemini_reasoning_service import (
    ActionItem,
    ActionItemExtraction,
    DeadlineSignal,
    EmailSignalsExtraction,
    GeminiReasoningService,
    MeetingProposal,
    SupervisorPlan,
)


def test_supervisor_plan_accepts_typed_specialist_tasks() -> None:
    plan = SupervisorPlan.model_validate(
        {
            "tasks": [
                {
                    "intent": "GET_URGENT_EMAILS",
                    "entities": {"important_only": True},
                    "description": "Read important emails",
                },
                {
                    "intent": "GET_TODAY_SCHEDULE",
                    "entities": {"date": "today"},
                    "description": "Read today's calendar",
                },
            ]
        }
    )

    assert [task.intent for task in plan.tasks] == [
        "GET_URGENT_EMAILS",
        "GET_TODAY_SCHEDULE",
    ]


def test_gemini_is_disabled_during_automated_tests(tmp_path) -> None:
    key_file = tmp_path / "gemini-key.txt"
    key_file.write_text("test-key-that-must-never-be-called", encoding="utf-8")
    service = GeminiReasoningService(api_key_file=key_file)

    assert service.configured() is False
    assert service.plan("Read my email") is None


def test_transcription_falls_back_and_uses_command_specific_prompt(monkeypatch, tmp_path) -> None:
    service = GeminiReasoningService(
        api_key_file=tmp_path / "unused-key.txt",
        transcription_model="quota-limited-model",
        model="fallback-model",
    )
    monkeypatch.setattr(service, "_api_key", lambda: "test-key")

    calls: list[dict] = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            if kwargs["model"] == "quota-limited-model":
                raise RuntimeError("quota exhausted")
            return SimpleNamespace(
                text="Send an email to alice@example.com saying hello"
            )

    class FakeClient:
        models = FakeModels()

        def close(self) -> None:
            pass

    monkeypatch.setattr(service, "_client", lambda api_key: FakeClient())

    transcript = service.transcribe_audio(b"valid audio bytes", "audio/webm")

    assert transcript == "Send an email to alice@example.com saying hello"
    assert [call["model"] for call in calls] == [
        "quota-limited-model",
        "fallback-model",
    ]
    assert "imperative verbs" in calls[0]["contents"][0]
    assert "name@gmail.com" in calls[0]["contents"][0]
    assert calls[0]["config"].temperature == 0
    assert service.last_error is None


def test_transcription_does_not_retry_the_same_model(monkeypatch, tmp_path) -> None:
    service = GeminiReasoningService(
        api_key_file=tmp_path / "unused-key.txt",
        transcription_model="same-model",
        model="same-model",
    )
    monkeypatch.setattr(service, "_api_key", lambda: "test-key")
    attempted_models: list[str] = []

    class FakeModels:
        def generate_content(self, **kwargs):
            attempted_models.append(kwargs["model"])
            raise RuntimeError("unavailable")

    class FakeClient:
        models = FakeModels()

        def close(self) -> None:
            pass

    monkeypatch.setattr(service, "_client", lambda api_key: FakeClient())

    assert service.transcribe_audio(b"valid audio bytes", "audio/wav") is None
    assert attempted_models == ["same-model"]
    assert service.last_error == "TranscriptionUnavailable: same-model: RuntimeError"


def test_email_extractors_use_typed_structured_responses(monkeypatch, tmp_path) -> None:
    service = GeminiReasoningService(api_key_file=tmp_path / "unused-key.txt")
    monkeypatch.setattr(service, "_api_key", lambda: "test-key")
    responses = [
        SimpleNamespace(
            parsed=ActionItemExtraction(
                items=[ActionItem(description="Send the invoice", due_date="Friday")]
            )
        ),
        SimpleNamespace(
            parsed=MeetingProposal(
                participant_name="Alice",
                participant_email="alice@example.com",
                date="Tuesday",
                time="4 pm",
            )
        ),
    ]
    calls: list[dict] = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return responses.pop(0)

    class FakeClient:
        models = FakeModels()

        def close(self) -> None:
            pass

    monkeypatch.setattr(service, "_client", lambda api_key: FakeClient())
    email = {
        "id": "email-1",
        "sender": "alice@example.com",
        "subject": "Follow-up",
        "body": "Please send the invoice by Friday. Does Tuesday at 4 pm work?",
    }

    items = service.extract_action_items(email)
    proposal = service.detect_meeting_proposal(email)

    assert items[0].description == "Send the invoice"
    assert proposal is not None
    assert proposal.time == "4 pm"
    assert all(call["config"].response_mime_type == "application/json" for call in calls)
    assert calls[0]["config"].response_schema is ActionItemExtraction
    assert calls[1]["config"].response_schema is MeetingProposal
    assert "untrusted" in calls[0]["config"].system_instruction


def test_email_signal_extractor_combines_deadline_without_a_third_email_call(monkeypatch, tmp_path) -> None:
    service = GeminiReasoningService(api_key_file=tmp_path / "unused-key.txt")
    monkeypatch.setattr(service, "_api_key", lambda: "test-key")
    calls: list[dict] = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                parsed=EmailSignalsExtraction(
                    deadline=DeadlineSignal(
                        has_deadline=True,
                        deadline_date="Friday",
                        deadline_description="the SIS discussion",
                    )
                )
            )

    class FakeClient:
        models = FakeModels()

        def close(self) -> None:
            pass

    monkeypatch.setattr(service, "_client", lambda api_key: FakeClient())

    signals = service.extract_email_signals(
        {
            "id": "email-1",
            "sender": "alice@example.com",
            "subject": "SIS discussion",
            "body": "Please finish this before Friday.",
        }
    )

    assert signals.deadline.has_deadline is True
    assert signals.deadline.deadline_date == "Friday"
    assert len(calls) == 1
    assert calls[0]["config"].response_schema is EmailSignalsExtraction
