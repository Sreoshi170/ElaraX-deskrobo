"""Generic confirmation-state handling for consequential actions."""

from backend.graphs.state import AetherBotState


def confirmation_node(state: AetherBotState) -> AetherBotState:
    """Keep, approve, or reject a prepared action without executing tools."""

    pending = state.get("pending_action")
    decision = state.get("confirmation_status")
    if not pending or decision == "pending":
        return {}
    if decision == "rejected":
        return {"pending_action": None, "final_response": "Action cancelled."}
    approved = dict(pending)
    approved["approved"] = True
    return {"pending_action": approved}

