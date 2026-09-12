"""State initialization and deterministic conversational reference helpers."""

import re
from difflib import SequenceMatcher
from typing import Any, Optional

from backend.graphs.state import AetherBotState


_ORDINALS = {
    "first": 0,
    "1st": 0,
    "second": 1,
    "2nd": 1,
    "third": 2,
    "3rd": 2,
    "fourth": 3,
    "4th": 3,
    "fifth": 4,
    "5th": 4,
    "sixth": 5,
    "6th": 5,
    "seventh": 6,
    "7th": 6,
    "eighth": 7,
    "8th": 7,
    "ninth": 8,
    "9th": 8,
    "tenth": 9,
    "10th": 9,
}


def _referenced_index(text: str, noun_pattern: str) -> Optional[int]:
    number = re.search(rf"\b(?:{noun_pattern})\s*#?\s*(\d+)\b", text)
    if not number:
        number = re.search(rf"\b(\d+)(?:st|nd|rd|th)?\s+(?:{noun_pattern}|one)\b", text)
    if number:
        return max(0, int(number.group(1)) - 1)
    for word, index in _ORDINALS.items():
        if re.search(rf"\b(?:the\s+)?{re.escape(word)}\s+(?:{noun_pattern}|one)\b", text):
            return index
    return None


def resolve_email_reference(
    text: str,
    emails: list[dict[str, Any]],
    active_email_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Resolve ordinal and pronoun references against the last visible email list."""

    lowered = text.casefold()
    index = _referenced_index(lowered, "email|message")
    if index is None and re.search(r"\b(?:last|latest|recent)\s+(?:email|message|one)\b", lowered):
        index = 0
    if index is not None and 0 <= index < len(emails):
        email = emails[index]
        return {
            "target_email_id": email.get("id"),
            "target_email_thread_id": email.get("thread_id"),
            "email_reference_index": index,
        }
    if re.search(
        r"\b(?:it|this email|that email|the email|same email|this message|that message|reply to it)\b",
        lowered,
    ) and active_email_id:
        return {"target_email_id": active_email_id}
    if re.search(r"\b(?:reply|respond|read|open|summarize)\b", lowered):
        ignored = {
            "reply",
            "respond",
            "read",
            "open",
            "summarize",
            "email",
            "message",
            "recent",
            "latest",
            "first",
            "second",
            "third",
            "this",
            "that",
            "the",
            "make",
            "draft",
            "write",
        }
        request_tokens = {
            token
            for token in re.findall(r"[\w]+", lowered)
            if len(token) >= 4 and token not in ignored
        }
        for email in emails:
            searchable = " ".join(
                str(email.get(field) or "")
                for field in ("sender_name", "sender", "subject")
            ).casefold()
            candidate_tokens = {token for token in re.findall(r"[\w]+", searchable) if len(token) >= 4}
            if any(
                request_token in candidate_tokens
                or any(
                    abs(len(request_token) - len(candidate_token)) <= 2
                    and SequenceMatcher(None, request_token, candidate_token).ratio() >= 0.82
                    for candidate_token in candidate_tokens
                )
                for request_token in request_tokens
            ):
                return {
                    "target_email_id": email.get("id"),
                    "target_email_thread_id": email.get("thread_id"),
                }
    return None


def resolve_event_reference(
    text: str,
    events: list[dict[str, Any]],
    active_event_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Resolve simple meeting/event references against recent calendar results."""

    lowered = text.casefold()
    index = _referenced_index(lowered, "meeting|event")
    if index is not None and 0 <= index < len(events):
        event = events[index]
        return {
            "event_id": event.get("id"),
            "target_event_id": event.get("id"),
            "event_reference_index": index,
        }
    if re.search(r"\b(?:this|that|the)\s+(?:meeting|event)\b", lowered) and active_event_id:
        return {"event_id": active_event_id, "target_event_id": active_event_id}
    if re.search(
        r"\b(?:meeting\s+link|join\s+(?:the\s+)?meeting|created\s+(?:the\s+)?meeting|new\s+meeting)\b",
        lowered,
    ):
        if active_event_id:
            return {"event_id": active_event_id, "target_event_id": active_event_id}
        if events:
            return {"event_id": events[0].get("id"), "target_event_id": events[0].get("id")}
    return None


def normalize_input_node(state: AetherBotState) -> AetherBotState:
    """Normalize whitespace and casing while retaining Unicode scripts."""

    raw_input = state.get("raw_input") or ""
    normalized = " ".join(raw_input.casefold().strip().split())
    return {"normalized_input": normalized}


def context_node(state: AetherBotState) -> AetherBotState:
    """Initialize collections and resolve references from prior graph state."""

    update: AetherBotState = {}
    if state.get("messages") is None:
        update["messages"] = []
    if state.get("entities") is None:
        update["entities"] = {}
    if state.get("tool_results") is None:
        update["tool_results"] = {}
    entities = dict(state.get("entities") or {})
    email_reference = resolve_email_reference(
        state.get("normalized_input") or "",
        state.get("retrieved_emails") or [],
        state.get("active_email_id"),
    )
    if email_reference:
        entities.update(email_reference)
        update["active_email_id"] = email_reference.get("target_email_id")
        if email_reference.get("target_email_thread_id"):
            update["active_email_thread_id"] = email_reference["target_email_thread_id"]
    event_reference = resolve_event_reference(
        state.get("normalized_input") or "",
        state.get("calendar_events") or [],
        state.get("active_calendar_event_id"),
    )
    if event_reference:
        entities.update(event_reference)
        update["active_calendar_event_id"] = event_reference.get("target_event_id")
    if entities != (state.get("entities") or {}):
        update["entities"] = entities
    return update
