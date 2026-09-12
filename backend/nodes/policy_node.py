"""Non-AI safety and confirmation policy."""

from backend.graphs.state import AetherBotState, RiskLevel


_READ_ONLY = {
    "CHECK_EMAIL",
    "READ_EMAIL",
    "READ_UNREAD_EMAILS",
    "FIND_EMAIL",
    "SUMMARIZE_EMAIL",
    "SUMMARIZE_THREAD",
    "PRIORITIZE_EMAILS",
    "GET_URGENT_EMAILS",
    "LIST_SENT_EMAILS",
    "LIST_DRAFT_EMAILS",
    "LIST_STARRED_EMAILS",
    "CHECK_CALENDAR",
    "GET_TODAY_SCHEDULE",
    "GET_TOMORROW_SCHEDULE",
    "CHECK_AVAILABILITY",
    "DAILY_BRIEFING",
    "STATUS",
    "GENERAL_QUERY",
    "HELP",
    "UNKNOWN",
    "MARKET_RESEARCH",
    "COMPETITOR_ANALYSIS",
    "SWOT_ANALYSIS",
}
_LOW_RISK = {"DRAFT_REPLY", "COMPOSE_EMAIL"}
_CONSEQUENTIAL = {
    "SEND_REPLY",
    "SEND_EMAIL",
    "FORWARD_EMAIL",
    "MARK_READ",
    "MARK_UNREAD",
    "STAR_EMAIL",
    "UNSTAR_EMAIL",
    "ARCHIVE_EMAIL",
    "TRASH_EMAIL",
    "DELETE_EMAIL",
    "CREATE_MEETING",
    "RESCHEDULE_MEETING",
    "CANCEL_MEETING",
}
_HIGH_RISK = {"MOVE_FORWARD", "MOVE_BACKWARD", "TURN_LEFT", "TURN_RIGHT", "COME_HERE", "LOOK_AT_USER"}


def policy_for_intent(intent: str) -> tuple[RiskLevel, bool]:
    if intent == "STOP":
        return "SAFETY_CRITICAL", False
    if intent in _HIGH_RISK:
        return "HIGH_RISK", True
    if intent in _CONSEQUENTIAL:
        return "CONSEQUENTIAL", True
    if intent in _LOW_RISK:
        return "LOW_RISK", False
    if intent in _READ_ONLY:
        return "READ_ONLY", False
    return "READ_ONLY", False


def policy_node(state: AetherBotState) -> AetherBotState:
    """Assign risk deterministically; an LLM cannot override this node."""

    risk_level, requires_confirmation = policy_for_intent(state.get("intent") or "UNKNOWN")
    return {
        "risk_level": risk_level,
        "requires_confirmation": requires_confirmation,
        "confirmation_status": "pending" if requires_confirmation else None,
    }
