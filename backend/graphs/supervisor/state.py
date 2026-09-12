"""Supervisor-specific state extensions for ElaraX orchestration."""

from typing import Any, Literal, Optional, TypedDict

from backend.graphs.state import AetherBotState


class AgentEnvelope(TypedDict, total=False):
    """Standard communication contract between supervisor and specialist agents.

    Follows the Aether pattern: every agent returns a uniform envelope so the
    supervisor can inspect status, merge context updates, and decide next steps.
    """

    agent: str
    status: Literal[
        "completed",
        "waiting_for_user",
        "error",
        "clarification_needed",
    ]
    result: dict[str, Any]
    context_updates: dict[str, Any]
    requires_approval: bool


class SupervisorGraphState(AetherBotState, total=False):
    """Extended state for the supervisor coordination graph."""

    # Ordered task plan produced by the planning node
    supervisor_plan: list[dict[str, Any]]
    # Index of the task currently being dispatched
    current_task_index: int
    # Which specialist agent is active for the current task
    current_agent: str
    # Accumulated results from all dispatched agents
    agent_results: list[AgentEnvelope]
    # Whether the supervisor should dispatch another agent
    needs_another_agent: bool
    # Combined final response assembled from all agent results
    supervisor_response: Optional[str]
