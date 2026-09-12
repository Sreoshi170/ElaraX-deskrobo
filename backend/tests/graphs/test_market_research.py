"""Contract tests for supervisor routing and source-grounded research."""

from fastapi.testclient import TestClient

from backend.api import app
from backend.graphs.graph_config import graph_run_config
from backend.graphs.master_graph import aetherbot_graph
from backend.nodes.intent_node import _classify, _deterministic_task_plan
from backend.services.market_research_service import market_research_service
from backend.services.llm_provider import llm_provider_service


def test_market_research_intents_are_semantic() -> None:
    assert _classify("Research the electric vehicle market") == "MARKET_RESEARCH"
    assert _classify("Analyze Tesla's competitors") == "COMPETITOR_ANALYSIS"
    assert _classify("Research Tesla and compare it with BYD") == "COMPETITOR_ANALYSIS"
    assert _classify("Give me a SWOT for the EV market") == "SWOT_ANALYSIS"


def test_research_compound_request_stays_one_supervisor_task(monkeypatch) -> None:
    monkeypatch.setattr(
        market_research_service,
        "retrieve_sources",
        lambda query, limit=8: [
            {"url": "https://example.test/ev", "title": "EV report", "snippet": "EV growth"}
        ],
    )
    result = aetherbot_graph.invoke(
        {
            "thread_id": "market-research-test",
            "raw_input": "Research the electric vehicle market and give me a SWOT analysis.",
            "input_source": "typed",
            "entities": {},
            "task_queue": [],
            "task_results": [],
            "tool_results": {},
        },
        config=graph_run_config("market-research-test"),
    )
    assert result["intent"] == "SWOT_ANALYSIS"
    assert len(result["task_results"]) == 1
    assert result["research_report"]["sources"][0]["url"] == "https://example.test/ev"
    assert result["research_report"]["swot"]["strengths"]


def test_research_endpoint_exposes_report_without_fake_sources(monkeypatch) -> None:
    monkeypatch.setattr(market_research_service, "retrieve_sources", lambda query, limit=8: [])
    client = TestClient(app)
    response = client.post("/api/research", json={"query": "Research solar energy trends"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["agent"] == "market_research"
    assert payload["research_report"]["sources"] == []
    assert payload["research_report"]["warnings"]


def test_openrouter_synthesis_is_merged_only_with_retrieved_evidence(monkeypatch) -> None:
    monkeypatch.setattr(
        market_research_service,
        "retrieve_sources",
        lambda query, limit=8: [
            {"url": "https://example.test/source", "title": "Source", "snippet": "Documented trend"}
        ],
    )
    monkeypatch.setattr(
        llm_provider_service,
        "generate_json",
        lambda **kwargs: {
            "executive_summary": "Evidence-backed summary.",
            "market_overview": "Evidence-backed overview.",
            "key_trends": ["Documented trend"],
            "competitors": ["Known competitor"],
            "swot": {
                "strengths": ["Evidence-backed strength"],
                "weaknesses": [],
                "opportunities": [],
                "threats": [],
            },
        },
    )
    result = market_research_service.research("Research the example market")
    assert result["report"]["analysis_provider"] == "openrouter"
    assert result["report"]["sources"][0]["url"] == "https://example.test/source"
