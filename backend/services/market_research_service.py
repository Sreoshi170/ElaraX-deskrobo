"""Source-grounded market research retrieval and report shaping.

The ZIP supplied with the project uses Tavily/DuckDuckGo, scraping and a
vector database.  Those are optional integrations in DeskRobo: this adapter
uses Tavily when configured, otherwise a lightweight DuckDuckGo endpoint.  It
does not fabricate fallback URLs or citations when retrieval is unavailable.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx

from backend.config import TAVILY_API_KEY, TAVILY_TIMEOUT_SECONDS, WILI_API_KEY, WILI_BASE_URL
from backend.services.llm_provider import llm_provider_service

logger = logging.getLogger("elarax.market_research")


def _clean_text(value: Any, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[:limit]


class MarketResearchService:
    def __init__(self) -> None:
        self.last_error: str | None = None

    def _tavily(self, query: str, limit: int) -> list[dict[str, Any]]:
        api_key = TAVILY_API_KEY
        if not api_key:
            return []
        response = httpx.post(
            "https://api.tavily.com/search",
            json={"query": query, "api_key": api_key, "max_results": limit},
            timeout=TAVILY_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        return [
            {"url": item.get("url"), "title": item.get("title"), "snippet": item.get("content")}
            for item in payload.get("results", [])
            if item.get("url")
        ]

    def _duckduckgo(self, query: str, limit: int) -> list[dict[str, Any]]:
        response = httpx.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=15.0,
        )
        response.raise_for_status()
        payload = response.json()
        results: list[dict[str, Any]] = []
        if payload.get("AbstractURL"):
            results.append(
                {
                    "url": payload.get("AbstractURL"),
                    "title": payload.get("Heading") or query,
                    "snippet": payload.get("AbstractText"),
                }
            )
        for item in payload.get("RelatedTopics", []):
            nested = item.get("Topics", []) if isinstance(item, dict) else []
            candidates = nested or [item]
            for candidate in candidates:
                if isinstance(candidate, dict) and candidate.get("FirstURL"):
                    results.append(
                        {
                            "url": candidate.get("FirstURL"),
                            "title": candidate.get("Text", "").split(" - ", 1)[0],
                            "snippet": candidate.get("Text"),
                        }
                    )
                    if len(results) >= limit:
                        return results
        return results[:limit]

    def _wili(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Use an explicitly configured Wili-compatible JSON search endpoint.

        Wili is not assumed by default because no public endpoint contract was
        present in the project. When configured, the adapter accepts common
        ``results``/``items`` payloads and still validates that every result
        has a real URL before exposing it as evidence.
        """

        if not (WILI_API_KEY and WILI_BASE_URL):
            return []
        response = httpx.get(
            WILI_BASE_URL,
            params={"q": query, "query": query, "limit": limit, "api_key": WILI_API_KEY},
            headers={"Authorization": f"Bearer {WILI_API_KEY}"},
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        candidates = payload.get("results") or payload.get("items") or []
        if isinstance(candidates, dict):
            candidates = candidates.get("results") or candidates.get("items") or []
        return [
            {
                "url": item.get("url") or item.get("link") or item.get("href"),
                "title": item.get("title") or item.get("name"),
                "snippet": item.get("snippet") or item.get("description") or item.get("content"),
            }
            for item in candidates
            if isinstance(item, dict) and (item.get("url") or item.get("link") or item.get("href"))
        ][:limit]

    def retrieve_sources(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        self.last_error = None
        if os.getenv("AETHERBOT_TESTING") == "1":
            return []
        results: list[dict[str, Any]] = []
        failures: list[str] = []
        selected_provider: str | None = None
        for provider_name, provider in (
            ("wili", self._wili),
            ("tavily", self._tavily),
            ("duckduckgo", self._duckduckgo),
        ):
            if provider_name == "wili" and not (WILI_API_KEY and WILI_BASE_URL):
                continue
            if provider_name == "tavily" and not TAVILY_API_KEY:
                continue
            try:
                results = provider(query, limit)
                if results:
                    selected_provider = provider_name
                    break
            except Exception as exc:  # optional external provider boundary
                failures.append(f"{provider_name}: {type(exc).__name__}")
                logger.warning("Market research %s retrieval failed: %s", provider_name, exc)
        if not results and failures:
            self.last_error = "Source providers unavailable (" + ", ".join(failures) + ")"

        unique: dict[str, dict[str, Any]] = {}
        for item in results:
            url = str(item.get("url") or "").strip()
            if not url or url in unique:
                continue
            unique[url] = {
                "url": url,
                "title": _clean_text(item.get("title") or url, 180),
                "snippet": _clean_text(item.get("snippet"), 700),
                # Keep the provenance tied to the provider that actually
                # returned this result.  A configured Wili endpoint may fail
                # and fall through to Tavily/DuckDuckGo.
                "source": selected_provider or "unknown",
            }
        return list(unique.values())[:limit]

    @staticmethod
    def _topic(query: str) -> str:
        topic = re.sub(
            r"\b(?:research|analy[sz]e|analysis|market research|give me|find|compare|show me|the|a|an|current|trends?|swot)\b",
            " ",
            query,
            flags=re.I,
        )
        topic = re.sub(r"\s+", " ", topic).strip(" .?!,:")
        topic = re.sub(r"\s+\b(?:and|with)\s*$", "", topic, flags=re.IGNORECASE).strip(" .?!,:")
        return topic or query.strip()

    @staticmethod
    def _swot(topic: str, sources: list[dict[str, Any]]) -> dict[str, list[str]]:
        if not sources:
            return {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}
        evidence = _clean_text(sources[0].get("snippet"), 220)
        return {
            "strengths": [f"Publicly documented information is available for {topic}."],
            "weaknesses": ["The available public evidence is limited and may not cover private company data."],
            "opportunities": ["Use the cited market sources to validate growth areas and customer segments."],
            "threats": ["Competitive, regulatory, and market conditions can change; verify before making decisions."],
        }

    @staticmethod
    def _business_profile(query: str) -> dict[str, str]:
        """Extract the optional owner brief embedded by the business intake UI."""
        profile: dict[str, str] = {}
        if "BUSINESS BRIEF" not in query.upper():
            return profile
        keys = ("business_name", "industry", "location", "stage", "offer", "customer", "problem", "goal", "budget", "competitors")
        labels = "|".join(key.replace("_", r"\s+") for key in keys)
        # The supervisor may normalize newlines to spaces. Parse both the
        # original multiline form and that single-line representation.
        pattern = re.compile(
            rf"(?:^|\s)(?P<key>{labels})\s*:\s*(?P<value>.*?)(?=\s+(?:{labels})\s*:|$)",
            flags=re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(query):
            key = re.sub(r"\s+", "_", match.group("key").strip().lower())
            value = _clean_text(match.group("value"), 600)
            if value:
                profile[key] = value
        return profile

    @staticmethod
    def _business_fallback(topic: str, profile: dict[str, str], sources: list[dict[str, Any]]) -> dict[str, list[str]]:
        offer = profile.get("offer") or topic
        customer = profile.get("customer") or "the target customer"
        location = profile.get("location") or "the target market"
        competitor_note = profile.get("competitors") or "established alternatives"
        return {
            "strengths": [f"A defined offer ({offer}) can be positioned around a specific customer need.", f"Owner context enables a focused go-to-market plan for {location}."],
            "weaknesses": [f"The offer must prove why {customer} should switch from {competitor_note}.", "Pricing, retention, unit economics, and operational capacity were not independently verified."],
            "opportunities": [f"Test a narrow segment of {customer} with a measurable pilot.", "Use the market signals in the sources to choose one differentiated promise and distribution channel."],
            "threats": [f"Competitors with more trust, distribution, or budget may copy the positioning in {location}.", "Demand, regulation, and acquisition costs can change quickly."],
        }

    @staticmethod
    def _business_actions(profile: dict[str, str]) -> dict[str, list[str]]:
        customer = profile.get("customer") or "one narrow customer segment"
        competitor = profile.get("competitors") or "the top two alternatives"
        goal = profile.get("goal") or "traction and retention"
        return {
            "recommendations": [
                f"Interview 10–15 people in {customer}; rank the three most painful needs before changing the product.",
                "Run a two-week paid pilot with one clear promise and track activation, repeat use, conversion, and gross margin.",
                f"Choose one measurable outcome tied to {goal} and review it weekly before expanding the offer or geography.",
            ],
            "competitive_strategy": [
                f"Create a comparison matrix for {competitor} across price, speed, quality, trust, and availability.",
                "Win a narrow wedge first: make one customer segment’s experience materially better instead of copying every competitor feature.",
                "Turn proof into a moat through testimonials, transparent service levels, retention programs, and partnerships in the target area.",
            ],
            "risks_and_assumptions": [
                "These owner-context recommendations are hypotheses, not verified market facts, because live source retrieval was unavailable.",
                "Validate willingness to pay, acquisition cost, repeat usage, delivery or service capacity, and regulatory requirements.",
            ],
            "next_steps": [
                "Days 1–30: interview customers, map competitors, define the differentiated promise, and establish baseline metrics.",
                "Days 31–60: run a paid pilot, test two acquisition channels, and remove the biggest delivery or product bottleneck.",
                "Days 61–90: double down on the best segment/channel combination and set a go/no-go scale decision using unit economics.",
            ],
        }

    def research(self, query: str, *, language: str = "en") -> dict[str, Any]:
        profile = self._business_profile(query)
        topic = (
            " / ".join(value for value in (profile.get("business_name"), profile.get("industry"), profile.get("location")) if value)
            if profile else self._topic(query)
        )
        retrieval_query = (
            "market size trends customers competitors pricing "
            + " ".join(value for key, value in profile.items() if key in {"industry", "location", "customer", "competitors"})
            if profile else query
        )
        sources = self.retrieve_sources(retrieval_query)
        warnings: list[str] = []
        if self.last_error:
            warnings.append("Live source retrieval was unavailable; no citations were inferred.")
        if not sources:
            warnings.append("No retrievable sources were returned. The report contains no invented citations.")

        trends = [item["snippet"] for item in sources[:5] if item.get("snippet")]
        report = {
            "query": query,
            "topic": topic,
            "status": "completed" if sources else "limited",
            "executive_summary": (
                f"Research on {topic} used {len(sources)} retrieved source(s)."
                if sources
                else f"I could not retrieve live sources for {topic}."
            ),
            "market_overview": (
                f"The retrieved evidence covers {topic}. Review the linked sources for the full context."
                if sources
                else "No market overview was generated because no source was retrieved."
            ),
            "key_trends": trends,
            "competitors": [],
            "swot": self._business_fallback(topic, profile, sources) if profile else self._swot(topic, sources),
            "business_profile": profile,
            **(self._business_actions(profile) if profile else {}),
            "sources": sources,
            "warnings": warnings,
            "sources_used_count": len(sources),
            # The deterministic fallback is English. A successful synthesis
            # records the requested language below; this lets the final
            # localization boundary translate fallback reports as well.
            "report_language": "en",
        }
        if sources:
            synthesized = llm_provider_service.generate_json(
                prompt=self._synthesis_prompt(query, topic, sources, language, profile),
                instruction=(
                    "You are a senior market research and startup strategy analyst. Use only the supplied source excerpts for market facts. "
                    "You may turn the owner's supplied business brief into clearly labeled hypotheses and actions, but do not present hypotheses as facts. "
                    "Do not invent citations, competitors, or URLs. If evidence is missing, "
                    "return an empty list or state that evidence is insufficient. Keep all URLs "
                    "exactly as supplied."
                ),
            )
            if synthesized:
                report = self._merge_synthesis(report, synthesized, sources, language)
            else:
                warnings.append("OpenRouter synthesis was unavailable; the report uses retrieval-only summaries.")
        report["warnings"] = warnings
        return {"report": report, "sources": sources, "warnings": warnings, "error": None}

    @staticmethod
    def _synthesis_prompt(
        query: str,
        topic: str,
        sources: list[dict[str, Any]],
        language: str = "en",
        profile: dict[str, str] | None = None,
    ) -> str:
        evidence = "\n\n".join(
            f"SOURCE {index}: {item['url']}\nTITLE: {item.get('title', '')}\nEXCERPT: {item.get('snippet', '')}"
            for index, item in enumerate(sources, start=1)
        )
        return (
            f"Research question: {query}\nTopic: {topic}\nResponse language: {language}\n\n"
            "Return JSON with exactly these keys: executive_summary (string), market_overview (string), "
            "key_trends (array of strings), competitors (array of strings), and swot (object with "
            "strengths, weaknesses, opportunities, threats arrays), recommendations (array of strings), "
            "competitive_strategy (array of strings), risks_and_assumptions (array of strings), and "
            "next_steps (array of strings). Write every user-facing value "
            "in the requested response language; preserve proper names and technical terms when "
            "needed. For each recommendation, include an action and the reason or metric to watch. "
            "Separate sourced findings from assumptions.\n\n"
            f"Owner business brief: {profile or 'None supplied'}\n\n"
            f"Retrieved evidence:\n{evidence}"
        )

    @staticmethod
    def _merge_synthesis(
        base: dict[str, Any],
        synthesized: dict[str, Any],
        sources: list[dict[str, Any]],
        language: str = "en",
    ) -> dict[str, Any]:
        merged = dict(base)
        for key in ("executive_summary", "market_overview"):
            if isinstance(synthesized.get(key), str) and synthesized[key].strip():
                merged[key] = synthesized[key].strip()
        for key in ("key_trends", "competitors", "recommendations", "competitive_strategy", "risks_and_assumptions", "next_steps"):
            value = synthesized.get(key)
            if isinstance(value, list):
                merged[key] = [str(item).strip() for item in value if str(item).strip()][:10]
        swot = synthesized.get("swot")
        if isinstance(swot, dict):
            merged["swot"] = {
                key: [str(item).strip() for item in (swot.get(key) or []) if str(item).strip()][:8]
                for key in ("strengths", "weaknesses", "opportunities", "threats")
            }
        if isinstance(synthesized.get("business_profile"), dict):
            merged["business_profile"] = base.get("business_profile") or synthesized["business_profile"]
        merged["analysis_provider"] = "openrouter"
        merged["report_language"] = language or "en"
        merged["sources"] = sources
        return merged

    @staticmethod
    def format_response(report: dict[str, Any]) -> str:
        if not report:
            return "No market research report was produced."
        return (
            f"Market research for {report.get('topic') or report.get('query')}: "
            f"{report.get('executive_summary', '')} "
            f"I prepared {len(report.get('recommendations') or [])} actionable recommendation(s) "
            f"I found {report.get('sources_used_count', 0)} source(s)."
        )


market_research_service = MarketResearchService()


def research_market(query: str) -> dict[str, Any]:
    """Convenience entry point for callers that do not need the service object."""

    return market_research_service.research(query)
