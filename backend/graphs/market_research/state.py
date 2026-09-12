"""Typed state for the source-grounded market research agent."""

from typing import Any, Literal, Optional, TypedDict


class MarketResearchState(TypedDict, total=False):
    query: str
    topic: str
    scope: str
    status: Literal["pending", "retrieving", "analyzing", "completed", "failed"]
    sources: list[dict[str, Any]]
    report: dict[str, Any]
    swot: dict[str, list[str]]
    warnings: list[str]
    error: Optional[str]

