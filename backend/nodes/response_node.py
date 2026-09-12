"""Final response normalization."""

from backend.graphs.state import AetherBotState
from backend.services.localization_service import localization_service


def response_node(state: AetherBotState) -> AetherBotState:
    """Ensure every branch produces a user-facing final response."""

    if state.get("final_response"):
        final_response = str(state["final_response"])
    elif state.get("error"):
        final_response = f"I couldn't complete that request: {state['error']}"
    elif state.get("requires_confirmation") and state.get("pending_action"):
        final_response = "This action is ready and waiting for your confirmation."
    else:
        final_response = "I understood the request, but no response was produced."

    language = state.get("response_language") or state.get("language_hint") or "en"
    localized_report = localization_service.localize_report(
        state.get("research_report") or {},
        language,
    )
    return {
        "final_response": localization_service.localize_text(final_response, language),
        **(
            {
                "research_report": localized_report,
                "research_result": localized_report,
                "swot": localized_report.get("swot"),
            }
            if localized_report and localized_report is not state.get("research_report")
            else {}
        ),
    }
