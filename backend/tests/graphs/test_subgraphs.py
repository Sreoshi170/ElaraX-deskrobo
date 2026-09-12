"""Graph-level tests for the mock domain subgraphs."""

from backend.graphs.briefing.graph import build_briefing_graph
from backend.graphs.calendar.graph import build_calendar_graph
from backend.graphs.email.graph import build_email_graph
from backend.graphs.robot.graph import build_robot_graph


def test_email_graph_reads_mock_data() -> None:
    result = build_email_graph().invoke({"intent": "GET_URGENT_EMAILS", "tool_results": {}})

    assert len(result["retrieved_emails"]) == 1
    assert result["retrieved_emails"][0]["urgent"] is True
    assert result["final_response"] == "I found 1 important email."


def test_email_graph_read_returns_message_content() -> None:
    result = build_email_graph().invoke({"intent": "READ_EMAIL", "tool_results": {}})

    assert result["retrieved_emails"][0]["body"]
    assert "From:" in result["final_response"]
    assert "Subject:" in result["final_response"]


def test_email_send_prepares_confirmation_without_sending() -> None:
    result = build_email_graph().invoke(
        {"intent": "SEND_REPLY", "requires_confirmation": True, "tool_results": {}}
    )

    assert result["pending_action"]["action"] == "SEND_REPLY"
    assert result["confirmation_status"] == "pending"
    assert "sent" in result["final_response"]
    assert "email_send" not in result["tool_results"]


def test_email_graph_composes_new_message_without_reading_the_inbox() -> None:
    result = build_email_graph().invoke(
        {
            "intent": "COMPOSE_EMAIL",
            "entities": {
                "participant_email": "hiring@example.com",
                "subject": "Interview",
                "body": "Thank you for your time.",
            },
            "retrieved_emails": [
                {
                    "id": "unrelated-email",
                    "thread_id": "unrelated-thread",
                    "sender": "someone@example.com",
                    "subject": "Unrelated inbox subject",
                }
            ],
            "tool_results": {},
        }
    )

    assert result["retrieved_emails"] == []
    assert result["tool_results"]["email_lookup"]["skipped"] is True
    assert result["reply_draft"] == "Thank you for your time."
    assert result["reply_draft_email_id"] is None
    assert "hiring@example.com" in result["final_response"]
    assert "Subject: Interview" in result["final_response"]
    assert result.get("pending_action") is None


def test_email_graph_prepares_new_send_for_confirmation() -> None:
    result = build_email_graph().invoke(
        {
            "intent": "SEND_EMAIL",
            "entities": {
                "participant_email": "sreoshibhowmik28@gmail.com",
                "body": "i love u bubu",
            },
            "tool_results": {},
        }
    )

    assert result["retrieved_emails"] == []
    assert result["pending_action"] == {
        "action": "SEND_EMAIL",
        "recipient": "sreoshibhowmik28@gmail.com",
        "subject": "No subject",
        "draft": "i love u bubu",
    }
    assert result["requires_confirmation"] is True
    assert result["confirmation_status"] == "pending"
    assert "Nothing has been sent yet" in result["final_response"]


def test_calendar_mutation_is_only_prepared() -> None:
    result = build_calendar_graph().invoke(
        {
            "intent": "CREATE_MEETING",
            "entities": {"participant": "rahul", "time": "4"},
            "tool_results": {},
        }
    )

    assert result["pending_action"]["action"] == "CREATE_MEETING"
    assert result["requires_confirmation"] is True
    assert "no event was changed" in result["final_response"]


def test_briefing_aggregates_mock_sources() -> None:
    result = build_briefing_graph().invoke({"tool_results": {}})

    assert len(result["retrieved_emails"]) == 1
    assert len(result["calendar_events"]) == 1
    assert "briefing" in result["tool_results"]


def test_robot_stop_executes_only_the_simulator() -> None:
    result = build_robot_graph().invoke(
        {
            "intent": "STOP",
            "robot_command": {"command": "STOP", "parameters": {}},
            "tool_results": {},
        }
    )

    assert result["robot_status"]["mock"] is True
    assert result["robot_status"]["status"] == "stopped"


def test_robot_motion_waits_for_confirmation() -> None:
    result = build_robot_graph().invoke({"intent": "TURN_LEFT", "tool_results": {}})

    assert result["pending_action"]["action"] == "ROBOT_COMMAND"
    assert result.get("robot_status") is None
    assert "not executed" in result["final_response"]
