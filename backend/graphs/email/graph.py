"""Construction of the mock Email LangGraph subgraph."""

from langgraph.graph import END, StateGraph

from backend.graphs.email.nodes import (
    draft_reply_node,
    email_action_router,
    email_response_node,
    fetch_emails_node,
    modify_email_node,
    summary_node,
)
from backend.graphs.email.routes import route_email_action
from backend.graphs.email.state import EmailGraphState


def build_email_graph():
    workflow = StateGraph(EmailGraphState)
    workflow.add_node("route_action", email_action_router)
    workflow.add_node("fetch_emails", fetch_emails_node)
    workflow.add_node("summarize", summary_node)
    workflow.add_node("draft", draft_reply_node)
    workflow.add_node("modify", modify_email_node)
    workflow.add_node("respond", email_response_node)

    workflow.set_entry_point("route_action")
    workflow.add_edge("route_action", "fetch_emails")
    workflow.add_conditional_edges(
        "fetch_emails",
        route_email_action,
        {"summarize": "summarize", "draft": "draft", "modify": "modify", "respond": "respond"},
    )
    workflow.add_edge("summarize", "respond")
    workflow.add_edge("draft", "respond")
    workflow.add_edge("modify", "respond")
    workflow.add_edge("respond", END)
    return workflow.compile()
