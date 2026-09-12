"""LangGraph wrapper for the market research specialist."""

from langgraph.graph import END, StateGraph

from backend.graphs.market_research.nodes import (
    market_research_response_node,
    run_market_research_node,
)
from backend.graphs.state import AetherBotState


def build_market_research_graph():
    workflow = StateGraph(AetherBotState)
    workflow.add_node("research", run_market_research_node)
    workflow.add_node("respond", market_research_response_node)
    workflow.set_entry_point("research")
    workflow.add_edge("research", "respond")
    workflow.add_edge("respond", END)
    return workflow.compile()


# Compatibility alias for the ZIP's ``build_graph`` convention.
build_graph = build_market_research_graph
