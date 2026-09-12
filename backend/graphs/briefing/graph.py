"""Construction of the Daily Briefing LangGraph subgraph."""

from langgraph.graph import END, StateGraph

from backend.graphs.briefing.nodes import briefing_response_node, load_briefing_sources_node
from backend.graphs.state import AetherBotState


def build_briefing_graph():
    workflow = StateGraph(AetherBotState)
    workflow.add_node("load_sources", load_briefing_sources_node)
    workflow.add_node("briefing_response", briefing_response_node)
    workflow.set_entry_point("load_sources")
    workflow.add_edge("load_sources", "briefing_response")
    workflow.add_edge("briefing_response", END)
    return workflow.compile()

