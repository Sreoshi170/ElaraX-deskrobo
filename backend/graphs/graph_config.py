"""Configuration helpers shared by compiled ElaraX graphs."""

from typing import Any

try:  # LangGraph >= 0.2
    from langgraph.checkpoint.memory import InMemorySaver
except ImportError:  # LangGraph 0.0.x compatibility for local development
    from langgraph.checkpoint.memory import MemorySaver as InMemorySaver


def create_checkpointer() -> Any:
    """Create an isolated in-memory checkpointer for a compiled graph."""

    return InMemorySaver()


def graph_run_config(thread_id: str) -> dict[str, dict[str, str]]:
    """Build the per-conversation configuration required by checkpointing."""

    return {"configurable": {"thread_id": thread_id}}
