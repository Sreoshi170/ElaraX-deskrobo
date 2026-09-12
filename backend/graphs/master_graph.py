"""Top-level ElaraX graph with supervisor-based agent orchestration.

The master graph routes through the Supervisor Agent (§7.1 of the ElaraX
context spec).  Emergency stop bypasses the supervisor and goes directly to
the robot safety path.
"""

from langgraph.graph import END, StateGraph

from backend.graphs.graph_config import create_checkpointer
from backend.graphs.robot.graph import build_robot_graph
from backend.graphs.state import AetherBotState
from backend.graphs.supervisor.graph import build_supervisor_graph
from backend.nodes.context_node import context_node, normalize_input_node
from backend.nodes.emergency_stop_node import emergency_stop_node, route_after_emergency_guard
from backend.nodes.language_node import language_node
from backend.nodes.response_node import response_node


def build_master_graph():
    """Build and compile the complete ElaraX workflow with supervisor agent.

    Pipeline::

        emergency_guard
            → (STOP) → robot → finalize_response → END
            → (continue) → language → normalize → context
                → supervisor → finalize_response → END
    """

    workflow = StateGraph(AetherBotState)

    # ── Pre-supervisor deterministic nodes ──
    workflow.add_node("emergency_guard", emergency_stop_node)
    workflow.add_node("language", language_node)
    workflow.add_node("normalize", normalize_input_node)
    workflow.add_node("context", context_node)

    # ── Supervisor agent (wraps all specialist agents internally) ──
    workflow.add_node("supervisor", build_supervisor_graph())

    # ── Emergency stop fast-path (bypasses supervisor) ──
    workflow.add_node("robot_stop", build_robot_graph())

    # ── Final response ──
    workflow.add_node("finalize_response", response_node)

    # ── Edges ──
    workflow.set_entry_point("emergency_guard")
    workflow.add_conditional_edges(
        "emergency_guard",
        route_after_emergency_guard,
        {"robot_stop": "robot_stop", "continue": "language"},
    )
    workflow.add_edge("robot_stop", "finalize_response")

    workflow.add_edge("language", "normalize")
    workflow.add_edge("normalize", "context")
    workflow.add_edge("context", "supervisor")
    workflow.add_edge("supervisor", "finalize_response")
    workflow.add_edge("finalize_response", END)

    return workflow.compile(checkpointer=create_checkpointer())


aetherbot_graph = build_master_graph()
