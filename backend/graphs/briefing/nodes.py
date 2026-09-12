"""Daily briefing aggregation nodes."""

from backend.graphs.state import AetherBotState
from backend.services import integration_service
from backend.services.google_auth_service import GoogleIntegrationError


def load_briefing_sources_node(state: AetherBotState) -> AetherBotState:
    email_service = integration_service.get_email_service()
    calendar_service = integration_service.get_calendar_service()
    try:
        important_emails = email_service.list_emails(max_results=10, important_only=True)
        meetings = calendar_service.list_events("today")
    except GoogleIntegrationError as exc:
        return {"error": str(exc)}
    briefing_data = {
        "critical_items": [email["subject"] for email in important_emails],
        "meetings": meetings,
        "important_emails": important_emails,
        "pending_actions": [state["pending_action"]] if state.get("pending_action") else [],
        "recommended_focus": "Review launch readiness before the afternoon deadline.",
    }
    return {
        "retrieved_emails": important_emails,
        "calendar_events": meetings,
        "tool_results": {**(state.get("tool_results") or {}), "briefing": briefing_data},
    }


def briefing_response_node(state: AetherBotState) -> AetherBotState:
    if state.get("error"):
        return {"final_response": state["error"]}
    emails = state.get("retrieved_emails") or []
    meetings = state.get("calendar_events") or []
    response = (
        f"Daily briefing: {len(emails)} important email(s) and "
        f"{len(meetings)} meeting(s) today. Focus on launch readiness."
    )
    return {"final_response": response}
