"""Construction of the safety-constrained Robot LangGraph subgraph."""

from langgraph.graph import END, StateGraph

from backend.graphs.robot.nodes import prepare_robot_command_node, robot_policy_node, robot_response_node
from backend.graphs.state import AetherBotState


def build_robot_graph():
    workflow = StateGraph(AetherBotState)
    workflow.add_node("prepare_command", prepare_robot_command_node)
    workflow.add_node("robot_policy", robot_policy_node)
    workflow.add_node("robot_response", robot_response_node)
    workflow.set_entry_point("prepare_command")
    workflow.add_edge("prepare_command", "robot_policy")
    workflow.add_edge("robot_policy", "robot_response")
    workflow.add_edge("robot_response", END)
    return workflow.compile()

