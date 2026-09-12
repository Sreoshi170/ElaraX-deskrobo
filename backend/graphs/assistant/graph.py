"""Construction of the general Assistant LangGraph subgraph."""

from langgraph.graph import END, StateGraph

from backend.graphs.assistant.nodes import assistant_response_node
from backend.graphs.state import AetherBotState


def build_assistant_graph():
    workflow = StateGraph(AetherBotState)
    workflow.add_node("assistant_response", assistant_response_node)
    workflow.set_entry_point("assistant_response")
    workflow.add_edge("assistant_response", END)
    return workflow.compile()

