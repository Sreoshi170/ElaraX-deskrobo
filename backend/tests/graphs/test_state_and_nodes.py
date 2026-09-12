"""Unit tests for shared state and deterministic control nodes."""

import pytest

from backend.graphs.state import AetherBotState
from backend.nodes.context_node import context_node, normalize_input_node
from backend.nodes.emergency_stop_node import emergency_stop_node, route_after_emergency_guard
from backend.graphs.supervisor.nodes import plan_tasks_node
from backend.nodes.intent_node import intent_node, route_by_intent
from backend.nodes.language_node import detect_language, language_node
from backend.nodes.policy_node import policy_node


def test_partial_state_creation_is_valid() -> None:
    state: AetherBotState = {"thread_id": "thread-1", "raw_input": "hello"}

    assert state["thread_id"] == "thread-1"
    assert "intent" not in state


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("what meetings do I have", "en"),
        ("আমার ইমেইল বলো", "bn"),
        ("आज मेरी बैठकें क्या हैं", "hi"),
        ("আমার email check করো", "mixed"),
        ("आज मेरी meetings क्या हैं", "mixed"),
        ("amar important email bolo", "bn"),
        ("aaj meri meetings kya hain", "hi"),
    ],
)
def test_language_detection(text: str, expected: str) -> None:
    assert detect_language(text) == expected
    assert language_node({"raw_input": text}) == {
        "input_language": expected,
        "response_language": expected,
    }


@pytest.mark.parametrize("command", ["stop", "stop moving!", "please halt now", "থামো।", "रुको!", "ruko"])
def test_emergency_stop_commands_bypass_confirmation(command: str) -> None:
    update = emergency_stop_node({"raw_input": command})

    assert update["intent"] == "STOP"
    assert update["risk_level"] == "SAFETY_CRITICAL"
    assert update["requires_confirmation"] is False
    assert update["robot_command"] == {"command": "STOP", "parameters": {}}
    assert route_after_emergency_guard(update) == "robot_stop"


@pytest.mark.parametrize(
    "sentence",
    ["don't stop checking email", "stop sending the reply", "the bus stop is nearby"],
)
def test_emergency_guard_avoids_broad_matches(sentence: str) -> None:
    update = emergency_stop_node({"raw_input": sentence})

    assert update == {}
    assert route_after_emergency_guard(update) == "continue"


@pytest.mark.parametrize(
    ("text", "intent", "route"),
    [
        ("what important emails do i have?", "GET_URGENT_EMAILS", "email"),
        ("Check my emails for meeting mentions", "CHECK_EMAIL", "email"),
        ("aaj meri meetings kya hain?", "GET_TODAY_SCHEDULE", "calendar"),
        ("reply the email", "DRAFT_REPLY", "email"),
        ("draft an email to alice@example.com saying hello", "COMPOSE_EMAIL", "email"),
        ('sent email to alice@example.com "hello"', "SEND_EMAIL", "email"),
        ("show my sent emails", "LIST_SENT_EMAILS", "email"),
        ("mark the email as unread", "MARK_UNREAD", "email"),
        ("archive the email", "ARCHIVE_EMAIL", "email"),
        ("not draft mail it", "GENERAL_QUERY", "assistant"),
        ("schedule a 30-minute meeting tomorrow at 4 pm", "CREATE_MEETING", "calendar"),
        ("daily briefing", "DAILY_BRIEFING", "briefing"),
        ("turn left", "TURN_LEFT", "robot"),
        ("help", "HELP", "assistant"),
    ],
)
def test_intent_classification_and_routing(text: str, intent: str, route: str) -> None:
    normalized = normalize_input_node({"raw_input": text})
    context = (
        {"active_email_id": "email-001"}
        if intent in {"MARK_UNREAD", "ARCHIVE_EMAIL"}
        else {}
    )
    update = intent_node({**normalized, **context})

    assert update["intent"] == intent
    assert route_by_intent(update) == route


def test_context_resolves_second_email_from_previous_results() -> None:
    update = context_node(
        {
            "normalized_input": "draft a reply to the second email",
            "entities": {},
            "retrieved_emails": [
                {"id": "email-1", "thread_id": "thread-1"},
                {"id": "email-2", "thread_id": "thread-2"},
            ],
        }
    )

    assert update["active_email_id"] == "email-2"
    assert update["active_email_thread_id"] == "thread-2"
    assert update["entities"]["target_email_id"] == "email-2"


def test_context_resolves_recent_email_to_newest_result() -> None:
    update = context_node(
        {
            "normalized_input": "reply to the recent email",
            "entities": {},
            "retrieved_emails": [
                {"id": "newest-email", "thread_id": "newest-thread"},
                {"id": "older-email", "thread_id": "older-thread"},
            ],
        }
    )

    assert update["entities"]["target_email_id"] == "newest-email"


def test_context_fuzzily_resolves_a_displayed_sender_name() -> None:
    update = context_node(
        {
            "normalized_input": "make a reply to mpocket",
            "entities": {},
            "retrieved_emails": [
                {
                    "id": "loan-email",
                    "thread_id": "loan-thread",
                    "sender_name": "mPokket",
                    "sender": "support@mpokket.example",
                    "subject": "Repayment receipt",
                }
            ],
        }
    )

    assert update["entities"]["target_email_id"] == "loan-email"
    assert update["entities"]["target_email_thread_id"] == "loan-thread"


def test_incomplete_meeting_request_asks_for_time() -> None:
    normalized = normalize_input_node({"raw_input": "book a meeting"})
    update = intent_node({**normalized, "raw_input": "book a meeting"})

    assert update["intent"] == "GENERAL_QUERY"
    assert "date and time" in update["supervisor_clarification"]


def test_mail_it_without_email_context_asks_for_target() -> None:
    normalized = normalize_input_node({"raw_input": "not draft mail it"})
    update = intent_node({**normalized, "raw_input": "not draft mail it"})

    assert update["intent"] == "GENERAL_QUERY"
    assert "Which email" in update["supervisor_clarification"]


def test_voice_style_email_address_and_draft_fields_are_extracted() -> None:
    raw_input = (
        "Draft an email to Alice dot Smith at Gmail dot com "
        "with subject Interview saying Thank you for your time"
    )
    normalized = normalize_input_node({"raw_input": raw_input})
    update = intent_node({**normalized, "raw_input": raw_input})

    assert update["intent"] == "COMPOSE_EMAIL"
    assert update["entities"]["participant_email"] == "alice.smith@gmail.com"
    assert update["entities"]["subject"] == "interview"
    assert update["entities"]["body"] == "thank you for your time"


def test_new_email_without_recipient_asks_for_email_address() -> None:
    raw_input = "Draft an email saying hello"
    normalized = normalize_input_node({"raw_input": raw_input})
    update = intent_node({**normalized, "raw_input": raw_input})

    assert update["intent"] == "GENERAL_QUERY"
    assert "email address" in update["supervisor_clarification"]


def test_voice_style_send_email_extracts_quoted_message() -> None:
    raw_input = 'sent email to sreoshibhowmik28@gmail.com "i love u bubu"'
    normalized = normalize_input_node({"raw_input": raw_input})
    update = intent_node({**normalized, "raw_input": raw_input})

    assert update["intent"] == "SEND_EMAIL"
    assert update["entities"]["participant_email"] == "sreoshibhowmik28@gmail.com"
    assert update["entities"]["body"] == "i love u bubu"


def test_voice_dictated_recipient_must_match_a_fetched_sender() -> None:
    state = {
        "raw_input": 'send email to lokeshhajraim28@gmail.com "hello"',
        "normalized_input": 'send email to lokeshhajraim28@gmail.com "hello"',
        "input_source": "voice",
        "retrieved_emails": [
            {"sender_name": "Lokesh", "sender": "lokesh.hajra@example.com"},
        ],
    }

    update = plan_tasks_node(state)

    assert update["intent"] == "GENERAL_QUERY"
    assert "could not verify" in update["supervisor_clarification"]


def test_forward_to_a_named_sender_uses_the_fetched_source_address() -> None:
    state = {
        "raw_input": "forward it to Lokesh",
        "normalized_input": "forward it to lokesh",
        "input_source": "typed",
        "active_email_id": "email-001",
        "retrieved_emails": [
            {
                "id": "email-001",
                "sender_name": "Lokesh Hajra",
                "sender": "lokesh.hajra@example.com",
            },
        ],
    }

    update = plan_tasks_node(state)

    assert update["intent"] == "FORWARD_EMAIL"
    assert update["entities"]["participant_email"] == "lokesh.hajra@example.com"


@pytest.mark.parametrize(
    ("intent", "risk", "confirmation"),
    [
        ("READ_EMAIL", "READ_ONLY", False),
        ("DRAFT_REPLY", "LOW_RISK", False),
        ("COMPOSE_EMAIL", "LOW_RISK", False),
        ("SEND_REPLY", "CONSEQUENTIAL", True),
        ("SEND_EMAIL", "CONSEQUENTIAL", True),
        ("CREATE_MEETING", "CONSEQUENTIAL", True),
        ("TURN_LEFT", "HIGH_RISK", True),
        ("STOP", "SAFETY_CRITICAL", False),
    ],
)
def test_deterministic_policy(intent: str, risk: str, confirmation: bool) -> None:
    update = policy_node({"intent": intent})

    assert update["risk_level"] == risk
    assert update["requires_confirmation"] is confirmation
