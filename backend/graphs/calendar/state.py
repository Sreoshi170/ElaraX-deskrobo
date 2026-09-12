"""Calendar-specific graph state."""

from typing import Literal

from backend.graphs.state import AetherBotState


class CalendarGraphState(AetherBotState, total=False):
    calendar_action: Literal["read", "create", "reschedule", "cancel"]

