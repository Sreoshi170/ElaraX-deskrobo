"""Shared state passed through every ElaraX LangGraph workflow."""

from typing import Any, Literal, Optional, TypedDict


LanguageCode = Literal["en", "bn", "hi", "mixed"]
LanguagePreference = Literal["auto", "en", "bn", "hi", "mixed"]
RiskLevel = Literal[
    "READ_ONLY",
    "LOW_RISK",
    "CONSEQUENTIAL",
    "HIGH_RISK",
    "SAFETY_CRITICAL",
]
ConfirmationStatus = Literal["pending", "approved", "rejected"]


class AetherBotState(TypedDict, total=False):
    """The shared, partially-updatable memory packet for ElaraX.

    ``total=False`` is important: each node returns only the fields it owns,
    and LangGraph merges those updates into the current graph state.
    """

    thread_id: str
    user_id: str
    messages: list[Any]

    raw_input: str
    normalized_input: str
    input_source: Literal["typed", "voice"]
    # Optional UI/STT preference. ``auto`` lets the deterministic detector
    # choose from English, Bengali, Hindi, and code-mixed input.
    language_hint: LanguagePreference
    input_language: LanguageCode
    response_language: LanguageCode

    intent: str
    intent_confidence: float
    entities: dict[str, Any]
    supervisor_mode: Literal["deterministic", "gemini"]
    supervisor_clarification: Optional[str]
    clarification_context: Optional[dict[str, Any]]
    supervisor_error: Optional[str]
    task_queue: list[dict[str, Any]]
    task_index: int
    task_results: list[dict[str, Any]]
    current_agent: Optional[str]
    needs_another_agent: bool
    supervisor_plan: list[dict[str, Any]]
    current_task_index: int
    agent_results: list[dict[str, Any]]

    # Source-grounded market research output shared with the API/UI.
    research_query: Optional[str]
    research_status: Optional[str]
    research_report: Optional[dict[str, Any]]
    research_result: Optional[dict[str, Any]]
    research_sources: list[dict[str, Any]]
    research_warnings: list[str]
    sources: list[dict[str, Any]]
    swot: Optional[dict[str, list[str]]]

    active_email_id: Optional[str]
    active_email_thread_id: Optional[str]
    active_calendar_event_id: Optional[str]

    retrieved_emails: list[dict[str, Any]]
    calendar_events: list[dict[str, Any]]
    detected_meeting_proposal: Optional[dict[str, Any]]
    active_meeting_proposal: Optional[dict[str, Any]]
    detected_deadline: Optional[dict[str, Any]]
    bridged_meeting_email_ids: list[str]
    bridged_deadline_email_ids: list[str]

    email_analysis: Optional[dict[str, Any]]
    email_summary: Optional[str]
    reply_draft: Optional[str]
    reply_draft_email_id: Optional[str]
    draft_recipient: Optional[str]
    draft_subject: Optional[str]
    draft_kind: Optional[Literal["new", "reply", "forward"]]

    pending_action: Optional[dict[str, Any]]
    risk_level: RiskLevel
    requires_confirmation: bool
    confirmation_status: Optional[ConfirmationStatus]

    robot_command: Optional[dict[str, Any]]
    robot_status: Optional[dict[str, Any]]
    tool_results: dict[str, Any]

    final_response: Optional[str]
    error: Optional[str]
