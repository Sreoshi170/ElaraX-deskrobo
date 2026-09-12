"""Supervisor nodes: plan, dispatch, and combine results from specialist agents.

Adapted from the Aether supervisor architecture to ElaraX's synchronous
LangGraph codebase.  The supervisor is the central coordinator described in
ElaraX context spec §7.1.  It plans ordered task queues, dispatches each to
the appropriate specialist subgraph, and merges the results into a unified
response.
"""

import logging
import re
from difflib import SequenceMatcher
from email.utils import parseaddr
from typing import Any

from backend.graphs.state import AetherBotState
from backend.nodes.context_node import resolve_email_reference, resolve_event_reference
from backend.nodes.intent_node import (
    _apply_current_draft_follow_up,
    CALENDAR_INTENTS,
    EMAIL_INTENTS,
    ROBOT_INTENTS,
    _continue_clarification,
    _classify,
    _deterministic_task_plan,
    _extract_entities,
    _should_use_gemini,
    MARKET_RESEARCH_INTENTS,
)
from backend.nodes.policy_node import policy_for_intent
from backend.services.gemini_reasoning_service import gemini_reasoning_service

logger = logging.getLogger("agents.supervisor")


def _address_from_source_email(email: dict[str, Any]) -> str:
    """Return a valid reply address from fetched email data, never a name guess."""

    _, address = parseaddr(str(email.get("reply_to") or email.get("sender") or ""))
    address = address.strip()
    if (
        address.count("@") != 1
        or any(character.isspace() for character in address)
        or "." not in address.rsplit("@", 1)[-1]
    ):
        return ""
    return address


def _known_recipient_addresses(state: AetherBotState) -> set[str]:
    """Collect only addresses previously fetched from the connected inbox."""

    return {
        address.casefold()
        for email in state.get("retrieved_emails") or []
        if (address := _address_from_source_email(email))
    }


def _named_source_recipient(text: str, state: AetherBotState) -> str:
    """Resolve `forward it to Lokesh` against fetched sender data.

    First tries exact word-subset matching.  If no exact match is found, falls
    back to SequenceMatcher fuzzy matching (ratio >= 0.75) on sender names.
    Ambiguous matches (more than one candidate) always return empty.
    """

    match = re.search(r"\bto\s+([a-z][a-z .'-]{1,80})(?=[,.!?;]|$)", text.casefold())
    if not match:
        return ""
    requested_name = match.group(1).strip()
    requested_words = set(re.findall(r"[a-z0-9]+", requested_name))
    if not requested_words:
        return ""

    exact_matches: list[str] = []
    fuzzy_matches: list[str] = []
    for email in state.get("retrieved_emails") or []:
        address = _address_from_source_email(email)
        if not address:
            continue
        sender_display = f"{email.get('sender_name') or ''} {email.get('sender') or ''}".casefold()
        sender_words = set(re.findall(r"[a-z0-9]+", sender_display))
        # Exact source-name token subset match
        if requested_words <= sender_words:
            exact_matches.append(address)
        else:
            # Fuzzy match: compare the requested name fragment against sender_name
            sender_name = str(email.get("sender_name") or "").casefold().strip()
            if sender_name and SequenceMatcher(None, requested_name, sender_name).ratio() >= 0.75:
                fuzzy_matches.append(address)
            # Also match against the local part of the email address
            local_part = address.split("@")[0].replace(".", " ").replace("-", " ").replace("_", " ").casefold()
            if local_part and SequenceMatcher(None, requested_name, local_part).ratio() >= 0.75:
                fuzzy_matches.append(address)

    # Prefer exact matches; fall back to fuzzy only if no exact match exists
    candidates = exact_matches or fuzzy_matches
    unique_matches = {address.casefold(): address for address in candidates}
    return next(iter(unique_matches.values())) if len(unique_matches) == 1 else ""


def _active_email_sender_fallback(state: AetherBotState) -> str:
    """Return the sender address of the active email when no recipient was named.

    If there is exactly one active email in context (via active_email_id), use
    its sender/reply-to address.  This avoids asking "What email address should
    I forward this to?" when the answer is already in the fetched data.
    """

    active_id = state.get("active_email_id")
    if not active_id:
        return ""
    for email in state.get("retrieved_emails") or []:
        if str(email.get("id")) == str(active_id):
            return _address_from_source_email(email)
    return ""


def _is_meeting_proposal_follow_up(text: str, state: AetherBotState) -> bool:
    if not state.get("active_meeting_proposal"):
        return False
    return bool(
        re.search(
            r"\b(?:book|schedule|create|confirm|accept)\s+(?:it|that|the\s+(?:proposed\s+)?meeting)\b",
            text,
        )
        or re.search(
            r"\b(?:go\s+ahead|sounds?\s+good|yes|yeah|yep|sure|ok|okay|let'?s?\s+do\s+it)\b",
            text,
        )
        and re.search(
            r"\b(?:book|schedule|create|confirm|meeting|slot|it)\b",
            text,
        )
        or re.search(r"\b(?:book|schedule|confirm)\s+(?:the\s+)?(?:\w+\s+)?slot\b", text)
    )


def _apply_active_meeting_proposal(
    task: dict[str, Any], text: str, state: AetherBotState
) -> dict[str, Any]:
    """Reuse a stored, source-backed proposal only for an explicit reference."""

    if not _is_meeting_proposal_follow_up(text, state):
        return task
    proposal = dict(state.get("active_meeting_proposal") or {})
    if not (proposal.get("date") and proposal.get("time")):
        return task
    entities = dict(task.get("entities") or {})
    for key in ("date", "time", "participant_name", "participant_email"):
        if proposal.get(key):
            entities.setdefault(key, proposal[key])
    if proposal.get("subject"):
        entities.setdefault("title", proposal["subject"])
    entities.setdefault("source_email_id", proposal.get("email_id"))
    task["intent"] = "CREATE_MEETING"
    task["entities"] = {key: value for key, value in entities.items() if value is not None}
    return task


def _task_signature(task: dict[str, Any]) -> tuple[str, tuple[tuple[str, str], ...]]:
    """Describe an operational task while ignoring presentation-only source text."""

    entities = {
        str(key): value
        for key, value in (task.get("entities") or {}).items()
        if key != "source"
    }
    return (
        str(task.get("intent") or "UNKNOWN"),
        tuple(sorted((key, repr(value)) for key, value in entities.items())),
    )


def _deduplicate_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one task for an identical operation within a user turn."""

    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    for task in tasks:
        signature = _task_signature(task)
        if signature in seen:
            continue
        seen.add(signature)
        deduplicated.append(task)
    return deduplicated

# ── Agent envelope helpers ──────────────────────────────────────────────

_AGENT_MAP: dict[str, str] = {
    "email": "email",
    "calendar": "calendar",
    "briefing": "briefing",
    "robot": "robot",
    "assistant": "assistant",
    "market_research": "market_research",
}


def _intent_to_agent(intent: str) -> str:
    """Map a classified intent to the correct specialist agent name."""

    if intent in EMAIL_INTENTS:
        return "email"
    if intent in CALENDAR_INTENTS:
        return "calendar"
    if intent == "DAILY_BRIEFING":
        return "briefing"
    if intent in ROBOT_INTENTS:
        return "robot"
    if intent in MARKET_RESEARCH_INTENTS:
        return "market_research"
    return "assistant"


def _meeting_clarification(task: dict[str, Any]) -> str:
    """Build a meeting-time question while preserving any safe slot suggestions."""

    entities = task.get("entities") or {}
    slots = entities.get("candidate_slots") or []
    if slots:
        labels = []
        for slot in slots[:3]:
            if isinstance(slot, dict):
                date_value = str(slot.get("date") or "").strip()
                time_value = str(slot.get("time") or "").strip()
                label = " ".join(value for value in (date_value, f"at {time_value}" if time_value else "") if value)
                if label:
                    labels.append(label)
        if labels:
            participant = str(
                entities.get("participant_name")
                or entities.get("participant")
                or entities.get("participant_email")
                or "the sender"
            ).strip()
            deadline = str(entities.get("deadline_date") or entities.get("date") or "the deadline").strip()
            description = str(entities.get("deadline_description") or "").strip()
            subject = f" about {description}" if description else ""
            return (
                f"{participant}'s email asks for a meeting{subject} before {deadline}. "
                f"I found these available slots: {', '.join(labels)}. Which slot should I book?"
            )
    return "What date and time should I use for the meeting?"


# ── Node 1: Plan tasks ─────────────────────────────────────────────────

def plan_tasks_node(state: AetherBotState) -> dict[str, Any]:
    """Classify intent & decompose multi-step commands into an ordered task plan.

    This node replaces the former ``intent_node`` when the supervisor graph is
    active.  It produces the same ``task_queue`` but also tags each task with the
    target ``agent`` field for dispatch and wraps everything in a
    ``supervisor_plan`` for the loop.
    """

    text = state.get("normalized_input") or ""
    deterministic_tasks = _deterministic_task_plan(text)
    tasks = deterministic_tasks
    supervisor_mode = "deterministic"
    clarification = None

    # Try Gemini planning for complex / multi-step requests
    if _should_use_gemini(text, deterministic_tasks):
        plan = gemini_reasoning_service.plan(
            state.get("raw_input") or text,
            language=state.get("input_language") or "en",
            context={
                "active_email_id": state.get("active_email_id"),
                "active_calendar_event_id": state.get("active_calendar_event_id"),
                "retrieved_emails": state.get("retrieved_emails") or [],
                "calendar_events": state.get("calendar_events") or [],
            },
        )
        if plan is not None:
            supervisor_mode = "gemini"
            clarification = plan.clarification
            if plan.tasks:
                tasks = [
                    {
                        "intent": task.intent,
                        "entities": {
                            **_extract_entities(text),
                            **dict(state.get("entities") or {}),
                            **task.entities.model_dump(exclude_none=True),
                        },
                        "description": task.description or text,
                    }
                    for task in plan.tasks
                ]
            elif clarification:
                tasks = [
                    {
                        "intent": "GENERAL_QUERY",
                        "entities": {**dict(state.get("entities") or {}), "source": text},
                        "description": text,
                    }
                ]

    # Merge existing entities and apply validation guards
    clarification_context = state.get("clarification_context")
    continued_tasks = _continue_clarification(text, state, deterministic_tasks)
    if continued_tasks:
        tasks = continued_tasks
        supervisor_mode = "deterministic"
        clarification = None

    existing_entities = dict(state.get("entities") or {})
    for task_index, task in enumerate(tasks):
        task["entities"] = {**existing_entities, **dict(task.get("entities") or {})}
        task = _apply_active_meeting_proposal(task, text, state)
        task = _apply_current_draft_follow_up(task, text, state)
        task_text = str(task.get("description") or text).casefold()
        if re.search(r"\bforward\b", task_text) and re.search(
            r"\b(?:email|mail|message|meeting\s+link|link)\b", task_text
        ):
            task["intent"] = "FORWARD_EMAIL"

        # Guard: meeting without time → try active proposal first, then ask
        if task.get("intent") in {"CREATE_MEETING", "RESCHEDULE_MEETING"} and not task["entities"].get("time"):
            # Attempt to fill from the stored meeting proposal before asking
            proposal = state.get("active_meeting_proposal") or {}
            if proposal.get("time"):
                task["entities"].setdefault("time", proposal["time"])
            if proposal.get("date"):
                task["entities"].setdefault("date", proposal["date"])
            for key in ("participant_name", "participant_email"):
                if proposal.get(key):
                    task["entities"].setdefault(key, proposal[key])
            if proposal.get("subject"):
                task["entities"].setdefault("title", proposal["subject"])
            # If time is still missing after proposal injection, ask the user
            if not task["entities"].get("time"):
                clarification_context = {
                    "intent": task.get("intent"),
                    "entities": dict(task["entities"]),
                    "description": task.get("description") or text,
                    "input_source": state.get("input_source"),
                }
                task["intent"] = "GENERAL_QUERY"
                clarification = clarification or _meeting_clarification(task)

        # Guard: compose without recipient
        if task.get("intent") == "COMPOSE_EMAIL" and not task["entities"].get("participant_email"):
            clarification_context = {
                "intent": task.get("intent"),
                "entities": dict(task["entities"]),
                "description": task.get("description") or text,
                "input_source": state.get("input_source"),
            }
            task["intent"] = "GENERAL_QUERY"
            clarification = clarification or "What email address should I draft this email to?"

        # Guard: send without recipient
        if task.get("intent") == "SEND_EMAIL" and not task["entities"].get("participant_email"):
            clarification_context = {
                "intent": task.get("intent"),
                "entities": dict(task["entities"]),
                "description": task.get("description") or text,
                "input_source": state.get("input_source"),
            }
            task["intent"] = "GENERAL_QUERY"
            clarification = clarification or "What email address should I send this email to?"

        # Guard: send without body
        if task.get("intent") == "SEND_EMAIL" and not task["entities"].get("body"):
            if not (state.get("draft_kind") == "new" and state.get("reply_draft")):
                clarification_context = {
                    "intent": task.get("intent"),
                    "entities": dict(task["entities"]),
                    "description": task.get("description") or text,
                    "input_source": state.get("input_source"),
                }
                task["intent"] = "GENERAL_QUERY"
                clarification = clarification or "What should the email say?"

        if task.get("intent") == "FORWARD_EMAIL" and not task["entities"].get("participant_email"):
            source_recipient = _named_source_recipient(task_text, state)
            if source_recipient:
                task["entities"]["participant_email"] = source_recipient
            else:
                # Fallback: if user said "forward it" without naming anyone,
                # use the active email's sender address when available.
                fallback = _active_email_sender_fallback(state)
                if fallback:
                    task["entities"]["participant_email"] = fallback

        # A transcribed address must match an address fetched from the inbox.
        # Typed addresses remain usable for new contacts and still require the
        # usual explicit send confirmation.
        # Also check the original input_source from clarification_context in
        # case the command was voice-originated but the follow-up turn is typed.
        original_input_source = str(
            (state.get("clarification_context") or {}).get("input_source")
            or state.get("input_source")
            or "typed"
        )
        if (
            original_input_source == "voice"
            and task.get("intent") in {"COMPOSE_EMAIL", "SEND_EMAIL", "FORWARD_EMAIL"}
            and task["entities"].get("participant_email")
            and str(task["entities"]["participant_email"]).casefold()
            not in _known_recipient_addresses(state)
        ):
            clarification_context = {
                "intent": task.get("intent"),
                "entities": dict(task["entities"]),
                "description": task.get("description") or text,
                "input_source": "voice",
            }
            task["intent"] = "GENERAL_QUERY"
            clarification = clarification or (
                "I could not verify that voice-dictated email address against a sender in your inbox. "
                "Please type the address exactly or choose a displayed email sender."
            )

        if task.get("intent") == "FORWARD_EMAIL" and not task["entities"].get("participant_email"):
            clarification_context = {
                "intent": task.get("intent"),
                "entities": dict(task["entities"]),
                "description": task.get("description") or text,
                "input_source": state.get("input_source"),
            }
            task["intent"] = "GENERAL_QUERY"
            clarification = clarification or "What email address should I forward this to?"
        if task.get("intent") == "FORWARD_EMAIL" and not (
            task["entities"].get("target_email_id")
            or state.get("active_email_id")
            or state.get("active_calendar_event_id")
            or state.get("calendar_events")
        ):
            clarification_context = {
                "intent": task.get("intent"),
                "entities": dict(task["entities"]),
                "description": task.get("description") or text,
                "input_source": state.get("input_source"),
            }
            task["intent"] = "GENERAL_QUERY"
            clarification = clarification or "Which email or meeting should I forward?"

        if task.get("intent") in {
            "MARK_READ",
            "MARK_UNREAD",
            "STAR_EMAIL",
            "UNSTAR_EMAIL",
            "ARCHIVE_EMAIL",
            "TRASH_EMAIL",
            "DELETE_EMAIL",
        } and not (task["entities"].get("target_email_id") or state.get("active_email_id")):
            clarification_context = {
                "intent": task.get("intent"),
                "entities": dict(task["entities"]),
                "description": task.get("description") or text,
                "input_source": state.get("input_source"),
            }
            task["intent"] = "GENERAL_QUERY"
            clarification = clarification or "Which email should I update?"

        # Guard: send reply without context
        if (
            task.get("intent") == "SEND_REPLY"
            and not task["entities"].get("target_email_id")
            and not task["entities"].get("email_query")
            and not (
                task["entities"].get("email_reference")
                and any(
                    previous_task.get("intent") in EMAIL_INTENTS
                    for previous_task in tasks[:task_index]
                )
            )
            and not state.get("active_email_id")
        ):
            clarification_context = {
                "intent": task.get("intent"),
                "entities": dict(task["entities"]),
                "description": task.get("description") or text,
            }
            task["intent"] = "GENERAL_QUERY"
            clarification = clarification or (
                "Which email should I send this reply to? Open or name the email, draft the reply, "
                "then ask me to mail it."
            )

        # Tag each task with the target agent for dispatch
        task["agent"] = _intent_to_agent(str(task.get("intent") or "UNKNOWN"))

    tasks = _deduplicate_tasks(tasks)
    first_task = tasks[0]
    intent = str(first_task.get("intent") or "UNKNOWN")
    confidence = 0.9 if supervisor_mode == "gemini" else (
        0.95 if intent not in {"GENERAL_QUERY", "UNKNOWN"} else 0.55
    )

    return {
        "intent": intent,
        "intent_confidence": confidence,
        "entities": dict(first_task.get("entities") or {}),
        "supervisor_mode": supervisor_mode,
        "supervisor_clarification": clarification,
        "clarification_context": None if continued_tasks else clarification_context,
        "supervisor_error": gemini_reasoning_service.last_error if supervisor_mode == "deterministic" else None,
        "task_queue": tasks,
        "task_index": 0,
        "task_results": [],
        # Supervisor-specific fields
        "supervisor_plan": tasks,
        "current_task_index": 0,
        "current_agent": str(first_task.get("agent") or "assistant"),
        "agent_results": [],
        "needs_another_agent": len(tasks) > 1,
    }


# ── Node 2: Resolve context references ─────────────────────────────────

def resolve_context_node(state: AetherBotState) -> dict[str, Any]:
    """Resolve email/event references in the current task before dispatch.

    Similar to Aether's ``resolve_context_node`` — ensures pronouns like
    'the first email' or 'that meeting' are connected to concrete IDs from
    prior graph state.
    """

    plan = state.get("supervisor_plan") or state.get("task_queue") or []
    current_idx = int(state.get("current_task_index") or 0)
    if current_idx >= len(plan):
        return {}

    current_task = dict(plan[current_idx])
    entities = dict(current_task.get("entities") or {})
    reference_text = " ".join(
        str(value)
        for value in (
            current_task.get("description"),
            entities.get("email_reference"),
            entities.get("event_reference"),
        )
        if value
    )

    # Resolve email references
    email_ref = resolve_email_reference(
        reference_text,
        state.get("retrieved_emails") or [],
        state.get("active_email_id"),
    )
    if email_ref:
        entities.update(email_ref)

    # Resolve event references
    event_ref = resolve_event_reference(
        reference_text,
        state.get("calendar_events") or [],
        state.get("active_calendar_event_id"),
    )
    if event_ref:
        entities.update(event_ref)

    # Write resolved entities back into the task
    current_task["entities"] = entities
    updated_plan = list(plan)
    updated_plan[current_idx] = current_task

    return {
        "entities": entities,
        "supervisor_plan": updated_plan,
        "task_queue": updated_plan,
    }


# ── Node 3: Dispatch decision ──────────────────────────────────────────

def dispatch_decision_node(state: AetherBotState) -> dict[str, Any]:
    """Prepare state for the current task's specialist agent dispatch.

    Sets ``intent``, ``entities``, and ``current_agent`` so the conditional
    edge router can send state to the correct specialist subgraph.
    """

    plan = state.get("supervisor_plan") or state.get("task_queue") or []
    current_idx = int(state.get("current_task_index") or 0)

    if current_idx >= len(plan):
        return {"current_agent": "assistant", "needs_another_agent": False}

    task = plan[current_idx]
    intent = str(task.get("intent") or "UNKNOWN")
    agent = str(task.get("agent") or _intent_to_agent(intent))

    risk_level, requires_confirmation = policy_for_intent(intent)

    return {
        "intent": intent,
        "entities": dict(task.get("entities") or {}),
        "current_agent": agent,
        "risk_level": risk_level,
        "requires_confirmation": requires_confirmation,
        "confirmation_status": "pending" if requires_confirmation else None,
        # Clear transient state from previous agent
        "final_response": None,
        "error": None,
        "email_summary": None,
        "email_analysis": None,
        "detected_meeting_proposal": None,
        "detected_deadline": None,
        "reply_draft": state.get("reply_draft") if intent in {"SEND_REPLY", "SEND_EMAIL", "FORWARD_EMAIL"} else None,
        "reply_draft_email_id": state.get("reply_draft_email_id") if intent in {"SEND_REPLY", "SEND_EMAIL", "FORWARD_EMAIL"} else None,
        "draft_recipient": state.get("draft_recipient") if intent in {"SEND_REPLY", "SEND_EMAIL", "FORWARD_EMAIL"} else None,
        "draft_subject": state.get("draft_subject") if intent in {"SEND_REPLY", "SEND_EMAIL", "FORWARD_EMAIL"} else None,
        "draft_kind": state.get("draft_kind") if intent in {"SEND_REPLY", "SEND_EMAIL", "FORWARD_EMAIL"} else None,
        "pending_action": None,
        "robot_command": None,
        "robot_status": None,
    }


def route_to_agent(state: AetherBotState) -> str:
    """Conditional edge router: send to the correct specialist subgraph."""

    return state.get("current_agent") or "assistant"


# ── Node 4: Collect result and decide next ──────────────────────────────

def collect_and_decide_node(state: AetherBotState) -> dict[str, Any]:
    """Collect the specialist agent's result and decide if more tasks remain.

    Follows Aether's sequential task execution pattern: after each agent
    finishes, the supervisor checks whether to continue, stop on error, or
    stop on a confirmation gate.
    """

    results = list(state.get("agent_results") or [])
    plan = state.get("supervisor_plan") or state.get("task_queue") or []
    current_idx = int(state.get("current_task_index") or 0)
    current_task = dict(plan[current_idx]) if current_idx < len(plan) else {}
    result_snapshot: dict[str, Any] = {
        "agent": state.get("current_agent") or "unknown",
        "status": "error" if state.get("error") else (
            "waiting_for_user" if state.get("pending_action") else "completed"
        ),
        "result": {
            "intent": state.get("intent"),
            "response": state.get("final_response"),
            "email_count": len(state.get("retrieved_emails") or []),
            "event_count": len(state.get("calendar_events") or []),
            "requires_confirmation": bool(state.get("requires_confirmation")),
            "error": state.get("error"),
            "research_report": state.get("research_report"),
            "sources": state.get("research_sources") or state.get("sources") or [],
        },
        "context_updates": {},
        "requires_approval": bool(state.get("requires_confirmation")),
        "task": current_task,
    }
    results.append(result_snapshot)

    # Also maintain task_results for backward compatibility
    task_results = list(state.get("task_results") or [])
    task_results.append({
        "agent": state.get("current_agent"),
        "intent": state.get("intent"),
        "response": state.get("final_response"),
        "email_count": len(state.get("retrieved_emails") or []),
        "event_count": len(state.get("calendar_events") or []),
        "requires_confirmation": bool(state.get("requires_confirmation")),
        "error": state.get("error"),
        "research_report": state.get("research_report"),
        "sources": state.get("research_sources") or state.get("sources") or [],
    })

    next_idx = current_idx + 1
    must_stop = bool(state.get("pending_action") or state.get("error"))
    updated_plan = list(plan)
    bridged_email_ids = list(state.get("bridged_meeting_email_ids") or [])
    bridged_deadline_ids = list(state.get("bridged_deadline_email_ids") or [])
    proposal = state.get("detected_meeting_proposal") or {}
    deadline = state.get("detected_deadline") or {}
    source_email_id = str(
        proposal.get("email_id")
        or proposal.get("source_email_id")
        or state.get("active_email_id")
        or ""
    ).strip()
    should_bridge = bool(
        not must_stop
        and state.get("current_agent") == "email"
        and state.get("intent") in EMAIL_INTENTS
        and proposal
        and source_email_id
        and source_email_id not in bridged_email_ids
        and next_idx <= len(updated_plan)
        and not deadline
    )
    if should_bridge:
        participant_name = str(
            proposal.get("participant_name")
            or proposal.get("sender")
            or proposal.get("participant_email")
            or "the sender"
        ).strip()
        bridge_entities = {
            key: proposal.get(key)
            for key in ("participant_name", "participant_email", "date", "time")
            if proposal.get(key)
        }
        bridge_entities["bridge_read_only"] = True
        bridge_task = {
            "intent": "CHECK_AVAILABILITY",
            "entities": bridge_entities,
            "agent": "calendar",
            "description": f"Check availability for the meeting proposed by {participant_name}",
            "bridge_source_email_id": source_email_id,
            "bridge_source_sender": proposal.get("participant_name") or proposal.get("sender") or participant_name,
        }
        if _task_signature(bridge_task) not in {_task_signature(task) for task in updated_plan}:
            updated_plan.append(bridge_task)
        bridged_email_ids.append(source_email_id)

    deadline_email_id = str(
        deadline.get("source_email_id")
        or deadline.get("email_id")
        or state.get("active_email_id")
        or ""
    ).strip()
    should_bridge_deadline = bool(
        not must_stop
        and state.get("current_agent") == "email"
        and state.get("intent") in EMAIL_INTENTS
        and deadline
        and deadline_email_id
        and deadline_email_id not in bridged_deadline_ids
    )
    deadline_waiting = False
    if should_bridge_deadline:
        participant_name = str(
            deadline.get("participant_name")
            or deadline.get("sender")
            or deadline.get("participant_email")
            or "the sender"
        ).strip()
        deadline_entities = {
            "participant": participant_name,
            "participant_name": participant_name,
            "participant_email": deadline.get("participant_email"),
            "date": deadline.get("deadline_date"),
            "deadline_date": deadline.get("deadline_date"),
            "deadline_description": deadline.get("deadline_description"),
            "candidate_slots": deadline.get("candidate_slots") or [],
            "duration_minutes": 30,
            "title": deadline.get("source_subject") or f"Meeting with {participant_name}",
            "source_email_id": deadline_email_id,
            "source_thread_id": deadline.get("source_thread_id"),
            "source_message_id": deadline.get("source_message_id"),
            "source_references": deadline.get("source_references"),
            "source_subject": deadline.get("source_subject"),
            "auto_reply_with_link": True,
            "source": f"Deadline detected in {deadline.get('source_subject') or 'an email'}",
        }
        deadline_task = {
            "intent": "CREATE_MEETING",
            # Keep the source keys present even when a provider has no Message-ID or References
            # header; the confirmation boundary can then preserve every available reply field.
            "entities": dict(deadline_entities),
            "agent": "calendar",
            "description": f"Schedule a meeting requested by {participant_name} before the email deadline",
            "bridge_source_email_id": deadline_email_id,
            "bridge_source_sender": participant_name,
            "deadline_bridge": True,
        }
        if _task_signature(deadline_task) not in {_task_signature(task) for task in updated_plan}:
            updated_plan.append(deadline_task)
        bridged_deadline_ids.append(deadline_email_id)
        deadline_waiting = True
        clarification_context = {
            "intent": "CREATE_MEETING",
            "entities": dict(deadline_task["entities"]),
            "description": deadline_task["description"],
        }
        clarification = _meeting_clarification(deadline_task)

    has_more = (not must_stop) and (not deadline_waiting) and (next_idx < len(updated_plan))

    return {
        "agent_results": results,
        "task_results": task_results,
        "current_task_index": next_idx,
        "task_index": next_idx,
        "needs_another_agent": has_more,
        "supervisor_plan": updated_plan,
        "task_queue": updated_plan,
        "bridged_meeting_email_ids": bridged_email_ids,
        "bridged_deadline_email_ids": bridged_deadline_ids,
        "supervisor_clarification": clarification if deadline_waiting else state.get("supervisor_clarification"),
        "clarification_context": clarification_context if deadline_waiting else state.get("clarification_context"),
    }


def route_after_collect(state: AetherBotState) -> str:
    """Continue the supervisor loop or finalize."""

    if state.get("needs_another_agent"):
        return "continue"
    return "finalize"


# ── Node 5: Combine results ────────────────────────────────────────────

def combine_results_node(state: AetherBotState) -> dict[str, Any]:
    """Merge all specialist results into a single user-facing response.

    For single-task plans, passes the agent's response through directly.
    For multi-task plans, numbers each step's response for clarity.
    Applies semantic deduplication to suppress near-identical availability
    checks and coalesces duplicate clarification questions.
    """

    results = state.get("agent_results") or []
    responses = [
        str(r.get("result", {}).get("response"))
        for r in results
        if r.get("result", {}).get("response")
    ]

    if len(responses) > 1:
        parts: list[str] = []
        clarifications: list[str] = []
        response_index = 0
        seen_responses: set[str] = set()
        seen_semantic: set[str] = set()
        for result in results:
            response = result.get("result", {}).get("response")
            if not response:
                continue
            response_str = str(response)
            # Exact normalized string dedup
            response_key = re.sub(r"\s+", " ", response_str).strip().casefold()
            if response_key in seen_responses:
                continue
            # Semantic dedup: strip availability keywords, dates, times, and
            # common status phrases to detect near-identical content.
            semantic_key = re.sub(
                r"\b\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)?\b", "", response_key
            )
            semantic_key = re.sub(
                r"\b(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                "", semantic_key,
            )
            semantic_key = re.sub(
                r"\b(?:appears?\s+(?:to\s+be\s+)?(?:available|free|open|busy))\b",
                "AVAIL", semantic_key,
            )
            semantic_key = re.sub(r"\s+", " ", semantic_key).strip()
            if semantic_key in seen_semantic and len(semantic_key) > 20:
                continue
            seen_responses.add(response_key)
            seen_semantic.add(semantic_key)
            task = result.get("task") or {}
            # Collect clarification questions separately to coalesce later
            if result.get("result", {}).get("intent") == "GENERAL_QUERY" and (
                response_str.endswith("?") or "should I" in response_str.casefold()
            ):
                if response_key not in {re.sub(r"\s+", " ", c).strip().casefold() for c in clarifications}:
                    clarifications.append(response_str)
                continue
            response_index += 1
            if task.get("bridge_source_email_id"):
                entities = task.get("entities") or {}
                proposal_time = " ".join(
                    str(entities.get(key)).strip()
                    for key in ("date", "time")
                    if entities.get(key)
                ) or "the proposed time"
                sender = task.get("bridge_source_sender") or "the sender"
                parts.append(f"I also noticed {sender} proposed {proposal_time} — {response}")
            else:
                parts.append(f"Step {response_index}: {response}")
        # Append unique clarification questions at the end, not as numbered steps
        for clarification_item in clarifications:
            if clarification_item not in " ".join(parts):
                parts.append(clarification_item)
        combined = " ".join(parts)
    elif responses:
        combined = responses[0]
    elif state.get("final_response"):
        combined = state["final_response"]
    elif state.get("supervisor_clarification"):
        combined = state["supervisor_clarification"]
    else:
        combined = "I understood the request, but no response was produced."

    clarification = state.get("supervisor_clarification")
    if clarification and state.get("clarification_context") and clarification not in combined:
        combined = f"{combined} {clarification}".strip()

    return {
        "final_response": combined,
        "supervisor_response": combined,
    }
