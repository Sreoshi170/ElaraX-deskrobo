"""Nodes for the market research specialist.

The graph deliberately keeps retrieval behind a small service boundary.  This
means optional web providers can fail safely and the UI never receives made-up
citations: a source is included only when the provider returned a URL.
"""

from typing import Any

from backend.graphs.state import AetherBotState
from backend.services.market_research_service import market_research_service


def _query_from_state(state: AetherBotState) -> str:
    entities = state.get("entities") or {}
    return str(
        entities.get("research_query")
        or entities.get("query")
        or entities.get("source")
        or state.get("raw_input")
        or ""
    ).strip()


def run_market_research_node(state: AetherBotState) -> AetherBotState:
    query = _query_from_state(state)
    if not query:
        return {
            "error": "Please provide a research question or market topic.",
            "final_response": "Please provide a research question or market topic.",
            "research_status": "failed",
        }

    result = market_research_service.research(
        query,
        language=state.get("response_language") or "en",
    )
    report = result.get("report") or {}
    sources = list(result.get("sources") or [])
    warnings = list(result.get("warnings") or [])
    error = result.get("error")
    return {
        "research_query": query,
        "research_report": report,
        "research_result": report,
        "research_status": "completed" if not error else "failed",
        "research_sources": sources,
        "sources": sources,
        "swot": report.get("swot") if isinstance(report, dict) else None,
        "research_warnings": warnings,
        "tool_results": {
            **(state.get("tool_results") or {}),
            "market_research": {
                "query": query,
                "sources": sources,
                "report": report,
                "warnings": warnings,
            },
        },
        "error": error,
    }


def market_research_response_node(state: AetherBotState) -> AetherBotState:
    report = state.get("research_report") or {}
    if state.get("error"):
        return {"final_response": f"I couldn't complete the market research: {state['error']}"}
    return {"final_response": market_research_service.format_response(report)}
