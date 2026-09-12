"""Fast, deterministic emergency STOP guard."""

import re

from backend.graphs.state import AetherBotState


_STOP_COMMANDS = {
    "stop",
    "stop moving",
    "halt",
    "thamo",
    "ruko",
    "থামো",
    "দাঁড়াও",
    "दाँड़ाओ",
    "रुको",
    "रुक",
    "बस",
}
_POLITE_TOKENS = {"please", "now", "the", "robot", "elarax", "elara", "aetherbot", "bot", "deskbot"}


def _normalize_stop_candidate(text: str) -> str:
    # Danda punctuation sits inside the Devanagari block, so remove it before
    # retaining the script ranges needed for Bengali and Hindi combining marks.
    without_danda = text.casefold().replace("।", " ").replace("॥", " ")
    cleaned = re.sub(r"[^\w\s\u0980-\u09ff\u0900-\u097f]", " ", without_danda)
    tokens = [token for token in cleaned.split() if token not in _POLITE_TOKENS]
    return " ".join(tokens)


def is_emergency_stop(text: str) -> bool:
    """Return true only for a standalone, explicit stop imperative."""

    return _normalize_stop_candidate(text) in _STOP_COMMANDS


def emergency_stop_node(state: AetherBotState) -> AetherBotState:
    """Prepare a STOP command before language or intent processing."""

    if not is_emergency_stop(state.get("raw_input") or ""):
        return {}
    return {
        "intent": "STOP",
        "intent_confidence": 1.0,
        "risk_level": "SAFETY_CRITICAL",
        "requires_confirmation": False,
        "robot_command": {"command": "STOP", "parameters": {}},
    }


def route_after_emergency_guard(state: AetherBotState) -> str:
    """Route STOP directly to the robot safety path."""

    return "robot_stop" if state.get("intent") == "STOP" else "continue"
