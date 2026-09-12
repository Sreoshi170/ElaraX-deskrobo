"""Task-loop nodes for executing an ordered supervisor plan through safe graphs."""

from typing import Any

from backend.graphs.state import AetherBotState
from backend.nodes.context_node import resolve_email_reference, resolve_event_reference


def _result_snapshot(state: AetherBotState) -> dict[str, Any]:
    return {
        "intent": state.get("intent"),
        "response": state.get("final_response"),
        "email_count": len(state.get("retrieved_emails") or []),
        "event_count": len(state.get("calendar_events") or []),
        "requires_confirmation": bool(state.get("requires_confirmation")),
        "error": state.get("error"),
    }


def collect_task_result_node(state: AetherBotState) -> AetherBotState:
    """Record one specialist result and prepare the next planned task, if safe."""

    results = [*(state.get("task_results") or []), _result_snapshot(state)]
    queue = state.get("task_queue") or []
    current_index = int(state.get("task_index") or 0)
    next_index = current_index + 1 if queue else 0
    must_stop = bool(state.get("pending_action") or state.get("error"))

    update: AetherBotState = {
        "task_results": results,
        "task_index": next_index,
    }
    if not must_stop and next_index < len(queue):
        next_task = queue[next_index]
        next_entities = dict(next_task.get("entities") or {})
        reference_text = " ".join(
            str(value)
            for value in (
                next_task.get("description"),
                next_entities.get("email_reference"),
                next_entities.get("event_reference"),
            )
            if value
        )
        email_reference = resolve_email_reference(
            reference_text,
            state.get("retrieved_emails") or [],
            state.get("active_email_id"),
        )
        if email_reference:
            next_entities.update(email_reference)
        event_reference = resolve_event_reference(
            reference_text,
            state.get("calendar_events") or [],
            state.get("active_calendar_event_id"),
        )
        if event_reference:
            next_entities.update(event_reference)
        update.update(
            {
                "intent": str(next_task.get("intent") or "UNKNOWN"),
                "entities": next_entities,
                "final_response": None,
                "error": None,
                "email_summary": None,
                "email_analysis": None,
                "reply_draft": None,
                "reply_draft_email_id": None,
                "pending_action": None,
                "requires_confirmation": False,
                "confirmation_status": None,
                "robot_command": None,
                "robot_status": None,
            }
        )
        return update

    responses = [str(item.get("response")) for item in results if item.get("response")]
    if len(responses) > 1:
        update["final_response"] = " ".join(
            f"Step {index}: {response}" for index, response in enumerate(responses, start=1)
        )
    elif responses:
        update["final_response"] = responses[0]
    return update


def route_after_task(state: AetherBotState) -> str:
    """Continue the task loop unless an error or approval gate pauses execution."""

    if state.get("pending_action") or state.get("error"):
        return "finish"
    queue = state.get("task_queue") or []
    next_index = int(state.get("task_index") or 0)
    return "next" if next_index < len(queue) else "finish"
