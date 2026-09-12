"""Deterministic routes within the email subgraph."""

from backend.graphs.email.state import EmailGraphState


def route_email_action(state: EmailGraphState) -> str:
    intent = state.get("intent") or "CHECK_EMAIL"
    if intent in {"SUMMARIZE_EMAIL", "SUMMARIZE_THREAD", "PRIORITIZE_EMAILS"}:
        return "summarize"
    if intent in {"DRAFT_REPLY", "SEND_REPLY", "COMPOSE_EMAIL", "SEND_EMAIL", "FORWARD_EMAIL"}:
        return "draft"
    if intent in {
        "MARK_READ",
        "MARK_UNREAD",
        "STAR_EMAIL",
        "UNSTAR_EMAIL",
        "ARCHIVE_EMAIL",
        "TRASH_EMAIL",
        "DELETE_EMAIL",
    }:
        return "modify"
    return "respond"
