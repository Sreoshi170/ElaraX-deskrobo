"""End-to-end routing tests for the compiled master graph."""

import pytest

from backend.graphs.graph_config import graph_run_config
from backend.graphs.email.nodes import _extract_email_signals
from backend.graphs.master_graph import build_master_graph
from backend.services.gemini_reasoning_service import DeadlineSignal, EmailSignalsExtraction, MeetingProposal


@pytest.mark.parametrize(
    ("raw_input", "expected_intent", "response_fragment"),
    [
        ("What important emails do I have?", "GET_URGENT_EMAILS", "1 important email"),
        ("Amar important emails bolo.", "GET_URGENT_EMAILS", "1 important email"),
        ("Aaj meri meetings kya hain?", "GET_TODAY_SCHEDULE", "Product stand-up"),
        ("daily briefing", "DAILY_BRIEFING", "Daily briefing"),
        ("help", "HELP", "mock email"),
    ],
)
def test_master_graph_routes_read_requests(
    raw_input: str, expected_intent: str, response_fragment: str
) -> None:
    graph = build_master_graph()
    thread_id = f"read-{expected_intent}-{raw_input}"

    result = graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": raw_input},
        config=graph_run_config(thread_id),
    )

    assert result["intent"] == expected_intent
    assert response_fragment in result["final_response"]


def test_master_graph_prepares_consequential_calendar_action() -> None:
    graph = build_master_graph()
    thread_id = "create-meeting"

    result = graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "Schedule meeting with Rahul tomorrow at 4.",
        },
        config=graph_run_config(thread_id),
    )

    assert result["intent"] == "CREATE_MEETING"
    assert result["risk_level"] == "CONSEQUENTIAL"
    assert result["pending_action"]["action"] == "CREATE_MEETING"
    assert result["confirmation_status"] == "pending"


def test_master_graph_executes_explicit_multi_step_plan_in_order() -> None:
    graph = build_master_graph()
    thread_id = "multi-step-read"

    result = graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "Show urgent emails, then show today's meetings.",
        },
        config=graph_run_config(thread_id),
    )

    assert [item["intent"] for item in result["task_results"]] == [
        "GET_URGENT_EMAILS",
        "GET_TODAY_SCHEDULE",
    ]
    assert "1 important email" in result["final_response"]
    assert "Product stand-up" in result["final_response"]


def test_master_graph_resolves_email_reference_across_turns() -> None:
    graph = build_master_graph()
    thread_id = "reply-reference"
    config = graph_run_config(thread_id)

    graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": "Show urgent emails."},
        config=config,
    )
    result = graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": "Draft a reply to the first email."},
        config=config,
    )

    assert result["intent"] == "DRAFT_REPLY"
    assert result["entities"]["target_email_id"] == "email-001"
    assert result["reply_draft"]
    assert result["final_response"].startswith("Draft:")


def test_master_graph_drafts_new_email_from_voice_style_command() -> None:
    graph = build_master_graph()
    thread_id = "voice-compose-email"
    raw_input = (
        "Draft an email to hiring at example dot com with subject Interview "
        "saying Thank you for your time"
    )

    result = graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": raw_input},
        config=graph_run_config(thread_id),
    )

    assert result["intent"] == "COMPOSE_EMAIL"
    assert result["entities"]["participant_email"] == "hiring@example.com"
    assert result["entities"]["subject"] == "interview"
    assert result["reply_draft"] == "thank you for your time"
    assert "hiring@example.com" in result["final_response"]
    assert result["requires_confirmation"] is False
    assert result.get("pending_action") is None


def test_master_graph_prepares_new_voice_email_send_for_confirmation() -> None:
    graph = build_master_graph()
    thread_id = "voice-send-email"
    raw_input = 'sent email to sreoshibhowmik28@gmail.com "i love u bubu"'

    result = graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": raw_input},
        config=graph_run_config(thread_id),
    )

    assert result["intent"] == "SEND_EMAIL"
    assert result["entities"]["participant_email"] == "sreoshibhowmik28@gmail.com"
    assert result["pending_action"]["action"] == "SEND_EMAIL"
    assert result["pending_action"]["draft"] == "i love u bubu"
    assert result["requires_confirmation"] is True
    assert "Nothing has been sent yet" in result["final_response"]


def test_explicit_mail_it_correction_reuses_draft_and_requires_confirmation() -> None:
    graph = build_master_graph()
    thread_id = "send-current-draft"
    config = graph_run_config(thread_id)

    graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": "Show urgent emails."},
        config=config,
    )
    draft_result = graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": "Reply to the first email."},
        config=config,
    )
    send_result = graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": "Not draft, mail it."},
        config=config,
    )

    assert send_result["intent"] == "SEND_REPLY"
    assert send_result["reply_draft"] == draft_result["reply_draft"]
    assert send_result["pending_action"]["action"] == "SEND_REPLY"
    assert send_result["pending_action"]["draft"] == draft_result["reply_draft"]
    assert send_result["requires_confirmation"] is True


def test_new_draft_can_be_sent_by_a_follow_up_without_repeating_recipient() -> None:
    graph = build_master_graph()
    thread_id = "send-new-draft-follow-up"
    config = graph_run_config(thread_id)

    draft_result = graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "Draft an email to lokeshhajraiem28@gmail.com with subject Meeting Link saying here is the link.",
        },
        config=config,
    )
    send_result = graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "Not in draft, send the email.",
        },
        config=config,
    )

    assert draft_result["intent"] == "COMPOSE_EMAIL"
    assert send_result["intent"] == "SEND_EMAIL"
    assert send_result["pending_action"]["recipient"] == "lokeshhajraiem28@gmail.com"
    assert send_result["pending_action"]["draft"] == "here is the link"


def test_meeting_time_clarification_keeps_email_recipient_out_of_calendar_details() -> None:
    graph = build_master_graph()
    thread_id = "meeting-clarification-follow-up"
    config = graph_run_config(thread_id)

    first = graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "Schedule a meeting about the discussion in the SIS account.",
        },
        config=config,
    )
    second = graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "The meeting time is 11 p.m. today and forward the mail to lokeshhajraiem28@gmail.com.",
        },
        config=config,
    )

    assert "date and time" in first["final_response"]
    assert second["intent"] == "CREATE_MEETING"
    assert second["entities"]["time"] == "11 pm"
    assert "participant_email" not in second["pending_action"]["details"]


def test_forward_meeting_link_uses_the_confirmed_calendar_event_context() -> None:
    graph = build_master_graph()
    thread_id = "forward-created-meeting-link"
    config = graph_run_config(thread_id)

    graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "Book a Google Meet at 11 am.",
        },
        config=config,
    )
    graph.update_state(
        config,
        {
            "calendar_events": [
                {
                    "id": "created-event",
                    "title": "SIS account discussion",
                    "time": "11:00 AM",
                    "meet_link": "https://meet.google.com/abc-defg-hij",
                }
            ],
            "active_calendar_event_id": "created-event",
        },
        as_node="finalize_response",
    )

    result = graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "Forward the meeting link that you created to lokeshhajraiem28@gmail.com.",
        },
        config=config,
    )

    assert result["intent"] == "FORWARD_EMAIL"
    assert result["pending_action"]["source_type"] == "calendar"
    assert "https://meet.google.com/abc-defg-hij" in result["pending_action"]["draft"]


def test_email_management_action_waits_for_confirmation() -> None:
    graph = build_master_graph()
    thread_id = "archive-selected-email"
    config = graph_run_config(thread_id)

    graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "Show urgent emails.",
        },
        config=config,
    )
    result = graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "Archive the email.",
        },
        config=config,
    )

    assert result["intent"] == "ARCHIVE_EMAIL"
    assert result["pending_action"]["action"] == "ARCHIVE_EMAIL"
    assert result["requires_confirmation"] is True


def test_email_meeting_proposal_dispatches_calendar_availability_in_same_run(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.graphs.email.nodes.gemini_reasoning_service.extract_action_items",
        lambda email: [],
    )
    monkeypatch.setattr(
        "backend.graphs.email.nodes.gemini_reasoning_service.detect_meeting_proposal",
        lambda email: MeetingProposal(
            participant_name="Alice",
            participant_email="alice@example.com",
            date="tomorrow",
            time="4 pm",
        ) if email.get("id") == "email-001" else None,
    )

    result = build_master_graph().invoke(
        {
            "thread_id": "meeting-proposal-bridge",
            "user_id": "test-user",
            "raw_input": "Show urgent emails.",
        },
        config=graph_run_config("meeting-proposal-bridge"),
    )

    assert [item["intent"] for item in result["task_results"]] == [
        "GET_URGENT_EMAILS",
        "CHECK_AVAILABILITY",
    ]
    assert "I also noticed Alice proposed tomorrow 4 pm" in result["final_response"]
    assert "appears available" in result["final_response"]
    assert result["requires_confirmation"] is False


def test_explicit_book_it_reuses_the_last_source_backed_meeting_proposal(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.graphs.email.nodes.gemini_reasoning_service.extract_email_signals",
        lambda email: EmailSignalsExtraction(
            meeting_proposal=MeetingProposal(
                participant_name="Alice",
                participant_email="fabricated@example.com",
                date="tomorrow",
                time="4 pm",
            )
            if email.get("id") == "email-001"
            else None,
        ),
    )
    graph = build_master_graph()
    thread_id = "book-last-meeting-proposal"
    config = graph_run_config(thread_id)

    graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": "Show urgent emails."},
        config=config,
    )
    result = graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": "Book it."},
        config=config,
    )

    assert result["intent"] == "CREATE_MEETING"
    assert result["pending_action"]["details"]["date"] == "tomorrow"
    assert result["pending_action"]["details"]["time"] == "4 pm"
    assert result["pending_action"]["details"]["participant_email"] == "alice@example.com"
    assert "What date and time" not in result["final_response"]


def test_combined_datetime_proposal_is_split_and_provider_errors_stay_hidden(monkeypatch) -> None:
    from backend.services.google_auth_service import GoogleIntegrationError

    class FailingAvailabilityService:
        provider_name = "google"

        def list_events(self, *args, **kwargs):
            return []

        def find_conflicts(self, details):
            raise GoogleIntegrationError("Use a meeting time such as 4 PM or 16:00.")

    monkeypatch.setattr(
        "backend.graphs.email.nodes.gemini_reasoning_service.extract_email_signals",
        lambda email: EmailSignalsExtraction(
            meeting_proposal=MeetingProposal(
                participant_name="Alice",
                participant_email="forged@example.com",
                time="2026-09-07 09:00:00",
            )
            if email.get("id") == "email-001"
            else None,
        ),
    )
    monkeypatch.setattr(
        "backend.graphs.email.nodes.integration_service.get_calendar_service",
        lambda: FailingAvailabilityService(),
    )

    result = build_master_graph().invoke(
        {
            "thread_id": "combined-datetime-proposal",
            "user_id": "test-user",
            "raw_input": "Show urgent emails.",
        },
        config=graph_run_config("combined-datetime-proposal"),
    )

    assert "Use a meeting time such as" not in result["final_response"]
    assert "could not verify" in result["final_response"]
    assert "2026-09-07 9:00 AM" in result["final_response"]
    assert result["task_results"][1]["error"] is None
    extracted = _extract_email_signals(
        [{"id": "email-001", "sender": "alice@example.com", "subject": "Launch review"}]
    )
    assert extracted["detected_meeting_proposal"]["participant_email"] == "alice@example.com"


def test_meeting_participant_address_comes_from_reply_to_not_model_output(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.graphs.email.nodes.gemini_reasoning_service.extract_email_signals",
        lambda email: EmailSignalsExtraction(
            meeting_proposal=MeetingProposal(
                participant_name="Forged name",
                participant_email="fabricated@example.com",
                date="tomorrow",
                time="4 pm",
            )
        ),
    )

    extracted = _extract_email_signals(
        [
            {
                "id": "email-001",
                "sender": "Lokesh <sender@example.com>",
                "reply_to": "reply-address@example.com",
                "subject": "Launch review",
            }
        ]
    )

    assert extracted["detected_meeting_proposal"]["participant_email"] == "reply-address@example.com"


def test_proposal_detection_is_cleared_before_a_different_email_turn(monkeypatch) -> None:
    class FakeEmailService:
        provider_name = "mock"

        def __init__(self) -> None:
            self.calls = 0

        def list_emails(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return [{
                    "id": "email-001",
                    "thread_id": "thread-001",
                    "sender": "alice@example.com",
                    "subject": "Launch review",
                    "snippet": "Does tomorrow at 4 pm work?",
                    "unread": True,
                    "urgent": True,
                }]
            return [{
                "id": "email-002",
                "thread_id": "thread-002",
                "sender": "kevin@example.com",
                "subject": "Deadline",
                "snippet": "Please review this by Friday.",
                "unread": True,
                "urgent": False,
            }]

        def get_email(self, message_id):
            return {}

    email_service = FakeEmailService()
    monkeypatch.setattr("backend.graphs.email.nodes.integration_service.get_email_service", lambda: email_service)
    monkeypatch.setattr(
        "backend.graphs.email.nodes.gemini_reasoning_service.extract_email_signals",
        lambda email: EmailSignalsExtraction(
            meeting_proposal=MeetingProposal(date="tomorrow", time="4 pm")
            if email.get("id") == "email-001"
            else None,
        ),
    )

    graph = build_master_graph()
    thread_id = "different-email-turn"
    config = graph_run_config(thread_id)
    graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": "Show urgent emails."},
        config=config,
    )
    second = graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": "Check my email for deadlines."},
        config=config,
    )

    assert second["active_email_id"] == "email-002"
    assert "Alice" not in second["final_response"]
    assert "proposed tomorrow 4 pm" not in second["final_response"]


def test_email_without_meeting_proposal_does_not_dispatch_calendar(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.graphs.email.nodes.gemini_reasoning_service.extract_action_items",
        lambda email: [],
    )
    monkeypatch.setattr(
        "backend.graphs.email.nodes.gemini_reasoning_service.detect_meeting_proposal",
        lambda email: None,
    )

    result = build_master_graph().invoke(
        {
            "thread_id": "no-meeting-proposal-bridge",
            "user_id": "test-user",
            "raw_input": "Show urgent emails.",
        },
        config=graph_run_config("no-meeting-proposal-bridge"),
    )

    assert [item["intent"] for item in result["task_results"]] == ["GET_URGENT_EMAILS"]


def test_email_deadline_offers_slots_then_preserves_auto_reply_context(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.graphs.email.nodes.gemini_reasoning_service.extract_email_signals",
        lambda email: EmailSignalsExtraction(
            deadline=DeadlineSignal(
                has_deadline=True,
                deadline_date="tomorrow",
                deadline_description="the SIS discussion",
            )
            if email.get("id") == "email-001"
            else DeadlineSignal(),
        ),
    )

    graph = build_master_graph()
    thread_id = "deadline-meeting-bridge"
    config = graph_run_config(thread_id)
    first = graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "Show urgent emails.",
        },
        config=config,
    )

    assert first.get("pending_action") is None
    assert "available slots" in first["final_response"]
    assert "Which slot should I book?" in first["final_response"]

    second = graph.invoke(
        {
            "thread_id": thread_id,
            "user_id": "test-user",
            "raw_input": "Tomorrow at 2 pm.",
        },
        config=config,
    )

    details = second["pending_action"]["details"]
    assert second["pending_action"]["action"] == "CREATE_MEETING"
    assert second["requires_confirmation"] is True
    assert "reply to their email" in second["final_response"]
    assert details["participant_email"] == "alice@example.com"
    assert details["source_email_id"] == "email-001"
    assert details["source_thread_id"] == "thread-001"
    assert details["auto_reply_with_link"] is True


def test_master_graph_holds_robot_motion_for_confirmation() -> None:
    graph = build_master_graph()
    thread_id = "turn-left"

    result = graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": "Turn left."},
        config=graph_run_config(thread_id),
    )

    assert result["intent"] == "TURN_LEFT"
    assert result["risk_level"] == "HIGH_RISK"
    assert result["robot_status"] is None
    assert result["pending_action"]["action"] == "ROBOT_COMMAND"


@pytest.mark.parametrize("stop_command", ["Stop.", "থামো।", "रुको।"])
def test_master_graph_emergency_stop_fast_path(stop_command: str) -> None:
    graph = build_master_graph()
    thread_id = f"stop-{stop_command}"

    result = graph.invoke(
        {"thread_id": thread_id, "user_id": "test-user", "raw_input": stop_command},
        config=graph_run_config(thread_id),
    )

    assert result["intent"] == "STOP"
    assert result["risk_level"] == "SAFETY_CRITICAL"
    assert result["requires_confirmation"] is False
    assert result["robot_status"]["status"] == "stopped"
