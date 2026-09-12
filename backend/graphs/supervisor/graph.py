"""Construction of the Supervisor LangGraph subgraph.

The supervisor is the central coordinator described in ElaraX context spec §7.1.
It wraps the existing specialist agents (email, calendar, briefing, robot,
assistant) behind a plan → resolve → dispatch → collect loop, following the
Aether supervisor architecture.

Flow::

    plan_tasks → resolve_context → dispatch_decision
        → [email|calendar|briefing|robot|assistant]
        → collect_and_decide
        → (loop back to resolve_context OR finalize)
        → combine_results → END
"""

from langgraph.graph import END, StateGraph

from backend.graphs.assistant.graph import build_assistant_graph
from backend.graphs.briefing.graph import build_briefing_graph
from backend.graphs.calendar.graph import build_calendar_graph
from backend.graphs.email.graph import build_email_graph
from backend.graphs.robot.graph import build_robot_graph
from backend.graphs.market_research.graph import build_market_research_graph
from backend.graphs.supervisor.state import SupervisorGraphState
from backend.graphs.supervisor.nodes import (
    collect_and_decide_node,
    combine_results_node,
    dispatch_decision_node,
    plan_tasks_node,
    resolve_context_node,
    route_after_collect,
    route_to_agent,
)


def build_supervisor_graph():
    """Build and compile the supervisor orchestration subgraph."""

    workflow = StateGraph(SupervisorGraphState)

    # ── Supervisor coordination nodes ──
    workflow.add_node("plan_tasks", plan_tasks_node)
    workflow.add_node("resolve_context", resolve_context_node)
    workflow.add_node("dispatch_decision", dispatch_decision_node)

    # ── Specialist agent subgraphs ──
    workflow.add_node("email", build_email_graph())
    workflow.add_node("calendar", build_calendar_graph())
    workflow.add_node("briefing", build_briefing_graph())
    workflow.add_node("robot", build_robot_graph())
    workflow.add_node("assistant", build_assistant_graph())
    workflow.add_node("market_research", build_market_research_graph())

    # ── Post-dispatch nodes ──
    workflow.add_node("collect_and_decide", collect_and_decide_node)
    workflow.add_node("combine_results", combine_results_node)

    # ── Edges ──
    workflow.set_entry_point("plan_tasks")
    workflow.add_edge("plan_tasks", "resolve_context")
    workflow.add_edge("resolve_context", "dispatch_decision")

    # Dispatch to the correct specialist agent
    workflow.add_conditional_edges(
        "dispatch_decision",
        route_to_agent,
        {
            "email": "email",
            "calendar": "calendar",
            "briefing": "briefing",
            "robot": "robot",
            "assistant": "assistant",
            "market_research": "market_research",
        },
    )

    # After each specialist, collect and decide
    for branch in ("email", "calendar", "briefing", "robot", "assistant", "market_research"):
        workflow.add_edge(branch, "collect_and_decide")

    # Loop back or finalize
    workflow.add_conditional_edges(
        "collect_and_decide",
        route_after_collect,
        {
            "continue": "resolve_context",
            "finalize": "combine_results",
        },
    )

    workflow.add_edge("combine_results", END)
    return workflow.compile()
