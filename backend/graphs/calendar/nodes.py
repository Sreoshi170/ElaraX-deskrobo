"""Deterministic calendar nodes backed by fixtures."""

import logging

from backend.graphs.calendar.state import CalendarGraphState
from backend.services import integration_service
from backend.services.google_auth_service import GoogleIntegrationError


_MUTATING_INTENTS = {"CREATE_MEETING", "RESCHEDULE_MEETING", "CANCEL_MEETING"}
logger = logging.getLogger("agents.calendar")


def calendar_action_node(state: CalendarGraphState) -> CalendarGraphState:
    intent = state.get("intent") or "CHECK_CALENDAR"
    day = "today" if intent == "GET_TODAY_SCHEDULE" else "tomorrow" if intent == "GET_TOMORROW_SCHEDULE" else None
    service = integration_service.get_calendar_service()
    entities = dict(state.get("entities") or {})
    try:
        events = service.list_events(day)
        conflicts = (
            service.find_conflicts(entities)
            if intent in {"CREATE_MEETING", "RESCHEDULE_MEETING", "CHECK_AVAILABILITY"}
            and entities.get("time")
            else []
        )
    except GoogleIntegrationError as exc:
        # The email bridge is an opportunistic, read-only enrichment. Do not
        # preserve a provider exception in graph state, where a later response
        # formatter could accidentally expose its raw message to the user.
        if entities.get("bridge_read_only"):
            logger.warning("Skipping auto-triggered calendar availability check: %s", exc)
            return {
                "calendar_events": [],
                "tool_results": {
                    **(state.get("tool_results") or {}),
                    "calendar_lookup": {
                        "ok": False,
                        "provider": service.provider_name,
                        "bridge_read_only": True,
                    },
                },
            }
        return {
            "error": str(exc),
            "calendar_events": [],
            "tool_results": {
                **(state.get("tool_results") or {}),
                "calendar_lookup": {"ok": False, "provider": service.provider_name},
            },
        }
    update: CalendarGraphState = {
        "calendar_events": events,
        "tool_results": {
            **(state.get("tool_results") or {}),
            "calendar_lookup": {
                "ok": True,
                "mock": service.provider_name == "mock",
                "provider": service.provider_name,
                "count": len(events),
                "conflicts": conflicts,
            },
        },
    }
    if events:
        update["active_calendar_event_id"] = events[0]["id"]
    if intent in _MUTATING_INTENTS:
        update["pending_action"] = {
            "action": intent,
            "details": entities,
            "conflicts": conflicts,
        }
        update["requires_confirmation"] = True
        update["confirmation_status"] = "pending"
    return update


def calendar_response_node(state: CalendarGraphState) -> CalendarGraphState:
    if state.get("error"):
        details = state.get("entities") or {}
        if details.get("bridge_read_only"):
            response = "I found a meeting proposal in the email, but I could not verify that time against your calendar."
        else:
            response = "I could not complete the calendar request. No calendar change was made."
        return {"final_response": response}
    if state.get("pending_action"):
        pending = state.get("pending_action", {})
        conflicts = pending.get("conflicts") or []
        conflict_note = f" I found {len(conflicts)} calendar conflict(s)." if conflicts else ""
        details = pending.get("details") or {}
        if pending.get("action") == "CREATE_MEETING" and details.get("auto_reply_with_link"):
            participant = details.get("participant_name") or details.get("participant_email") or "the sender"
            proposed_time = " ".join(
                str(details.get(key)).strip()
                for key in ("date", "time")
                if details.get(key)
            ) or "the selected time"
            return {
                "final_response": (
                    f"Book a meeting with {participant} at {proposed_time} and reply to their email "
                    "with the Google Meet link? This action is prepared and waiting for your confirmation; "
                    "nothing has been changed or sent yet."
                    + conflict_note
                )
            }
        return {
            "final_response": (
                "The calendar change is prepared and waiting for confirmation; no event was changed."
                + conflict_note
            )
        }
    if state.get("intent") == "CHECK_AVAILABILITY":
        lookup = (state.get("tool_results") or {}).get("calendar_lookup") or {}
        if not lookup.get("ok", False):
            return {
                "final_response": (
                    "I found a meeting proposal in the email, but I could not verify that time "
                    "against your calendar."
                )
            }
        conflicts = lookup.get("conflicts") or []
        details = state.get("entities") or {}
        proposed_time = " ".join(
            str(details.get(key)).strip()
            for key in ("date", "time")
            if details.get(key)
        )
        time_note = f" ({proposed_time})" if proposed_time else ""
        return {
            "final_response": (
                f"The proposed time{time_note} is busy."
                if conflicts
                else f"The proposed time{time_note} appears available."
            )
        }
    events = state.get("calendar_events") or []
    if not events:
        return {"final_response": "Your calendar has no matching events."}
    details = ", ".join(f"{event['title']} at {event['time']}" for event in events)
    return {"final_response": f"Your calendar shows: {details}."}
