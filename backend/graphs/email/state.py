"""Email-specific extensions to the shared graph state."""

from typing import Literal, TypedDict

from backend.graphs.state import AetherBotState


class EmailGraphState(AetherBotState, total=False):
    email_action: Literal["read", "summarize", "draft", "send", "modify"]
