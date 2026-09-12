"""Construction of the Calendar LangGraph subgraph."""

from langgraph.graph import END, StateGraph

from backend.graphs.calendar.nodes import calendar_action_node, calendar_response_node
from backend.graphs.calendar.state import CalendarGraphState


def build_calendar_graph():
    workflow = StateGraph(CalendarGraphState)
    workflow.add_node("perform_calendar_action", calendar_action_node)
    workflow.add_node("calendar_response", calendar_response_node)
    workflow.set_entry_point("perform_calendar_action")
    workflow.add_edge("perform_calendar_action", "calendar_response")
    workflow.add_edge("calendar_response", END)
    return workflow.compile()
