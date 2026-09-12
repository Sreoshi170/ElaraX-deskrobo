"""Replaceable deterministic intent classifier and graph router."""

import re
from collections.abc import Iterable
from typing import Any

from backend.graphs.state import AetherBotState
from backend.services.gemini_reasoning_service import gemini_reasoning_service


EMAIL_INTENTS = {
    "CHECK_EMAIL",
    "READ_EMAIL",
    "READ_UNREAD_EMAILS",
    "FIND_EMAIL",
    "SUMMARIZE_EMAIL",
    "SUMMARIZE_THREAD",
    "PRIORITIZE_EMAILS",
    "GET_URGENT_EMAILS",
    "DRAFT_REPLY",
    "SEND_REPLY",
    "COMPOSE_EMAIL",
    "SEND_EMAIL",
    "FORWARD_EMAIL",
    "LIST_SENT_EMAILS",
    "LIST_DRAFT_EMAILS",
    "LIST_STARRED_EMAILS",
    "MARK_READ",
    "MARK_UNREAD",
    "STAR_EMAIL",
    "UNSTAR_EMAIL",
    "ARCHIVE_EMAIL",
    "TRASH_EMAIL",
    "DELETE_EMAIL",
}
CALENDAR_INTENTS = {
    "CHECK_CALENDAR",
    "GET_TODAY_SCHEDULE",
    "GET_TOMORROW_SCHEDULE",
    "CHECK_AVAILABILITY",
    "CREATE_MEETING",
    "RESCHEDULE_MEETING",
    "CANCEL_MEETING",
}
ROBOT_INTENTS = {
    "MOVE_FORWARD",
    "MOVE_BACKWARD",
    "TURN_LEFT",
    "TURN_RIGHT",
    "COME_HERE",
    "LOOK_AT_USER",
    "STATUS",
    "STOP",
}
MARKET_RESEARCH_INTENTS = {
    "MARKET_RESEARCH",
    "COMPETITOR_ANALYSIS",
    "SWOT_ANALYSIS",
}

_GEMINI_ASSISTED_INTENTS = {
    "DRAFT_REPLY",
    "SEND_REPLY",
    "COMPOSE_EMAIL",
    "SEND_EMAIL",
    "FORWARD_EMAIL",
    "CREATE_MEETING",
    "RESCHEDULE_MEETING",
    "CANCEL_MEETING",
    "CHECK_CALENDAR",
    "CHECK_EMAIL",
    "GENERAL_QUERY",
    "UNKNOWN",
}


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    return any(phrase in text for phrase in phrases)


_EMAIL_ADDRESS_RE = re.compile(
    r"(?<![\w.+-])[a-z0-9][a-z0-9._%+-]*@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+",
    re.IGNORECASE,
)
_SPOKEN_EMAIL_RE = re.compile(
    r"\b([a-z0-9][a-z0-9_+%-]*(?:\s*(?:\.|\bdot\b)\s*[a-z0-9_+%-]+)*)"
    r"\s*(?:@|\bat(?:\s+the\s+rate)?\b)\s*"
    r"([a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    r"(?:\s*(?:\.|\bdot\b)\s*[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+)\b",
    re.IGNORECASE,
)


def _extract_email_address_details(text: str) -> tuple[str, int] | None:
    """Extract an address and its end offset from literal or speech-to-text forms."""

    literal_match = _EMAIL_ADDRESS_RE.search(text)
    if literal_match:
        return literal_match.group(0).lower(), literal_match.end()

    spoken_match = _SPOKEN_EMAIL_RE.search(text)
    if not spoken_match:
        return None

    local_part = re.sub(r"\s*(?:\.|\bdot\b)\s*", ".", spoken_match.group(1), flags=re.IGNORECASE)
    domain = re.sub(r"\s*(?:\.|\bdot\b)\s*", ".", spoken_match.group(2), flags=re.IGNORECASE)
    candidate = f"{local_part}@{domain}".lower()
    return (candidate, spoken_match.end()) if _EMAIL_ADDRESS_RE.fullmatch(candidate) else None


def _extract_email_address(text: str) -> str | None:
    """Extract literal or speech-to-text forms such as `name at gmail dot com`."""

    details = _extract_email_address_details(text)
    return details[0] if details else None


def _is_current_draft_request(text: str) -> bool:
    """Recognize short follow-ups such as 'not a draft, send it'."""

    return bool(
        re.search(
            r"\b(?:send|mail|email)\s+(?:it|this|that|the\s+(?:draft|email|message))\b",
            text,
        )
        or re.search(
            r"\bnot\s+(?:in\s+)?draft\b[\s,;:-]*(?:now\s+)?(?:send|mail|email)\b",
            text,
        )
    )


def _apply_current_draft_follow_up(
    task: dict[str, Any], text: str, state: AetherBotState
) -> dict[str, Any]:
    """Turn a current-draft follow-up into a send action with saved metadata."""

    if not state.get("reply_draft") or not _is_current_draft_request(text):
        return task
    if task.get("intent") not in {"SEND_REPLY", "SEND_EMAIL", "GENERAL_QUERY"}:
        return task
    draft_kind = state.get("draft_kind") or "reply"
    task["intent"] = {"new": "SEND_EMAIL", "forward": "FORWARD_EMAIL"}.get(
        draft_kind, "SEND_REPLY"
    )
    task_entities = dict(task.get("entities") or {})
    task_entities.setdefault("participant_email", state.get("draft_recipient"))
    task_entities.setdefault("subject", state.get("draft_subject"))
    task_entities.setdefault("body", state.get("reply_draft"))
    if state.get("reply_draft_email_id"):
        task_entities.setdefault("target_email_id", state.get("reply_draft_email_id"))
    task["entities"] = {
        key: value for key, value in task_entities.items() if value is not None
    }
    return task


def _continue_clarification(
    text: str, state: AetherBotState, current_tasks: list[dict[str, Any]]
) -> list[dict[str, Any]] | None:
    """Complete a prior clarification while retaining its original task context."""

    context = state.get("clarification_context") or {}
    original_intent = str(context.get("intent") or "")
    if not original_intent:
        return None
    entities = {
        **dict(context.get("entities") or {}),
        **_extract_entities(text),
        **dict(state.get("entities") or {}),
    }
    if original_intent in {"CREATE_MEETING", "RESCHEDULE_MEETING"} and re.search(
        r"\bforward\b", text
    ):
        entities.pop("participant_email", None)
        entities.pop("body", None)
    required = {
        "CREATE_MEETING": "time",
        "RESCHEDULE_MEETING": "time",
        "COMPOSE_EMAIL": "participant_email",
        "SEND_EMAIL": "participant_email",
    }
    if required.get(original_intent) and not entities.get(required[original_intent]):
        return None
    if original_intent == "SEND_EMAIL" and not entities.get("body"):
        return None
    original_task = {
        "intent": original_intent,
        "entities": {**entities, "source": f"{context.get('description') or ''} {text}".strip()},
        "description": str(context.get("description") or text),
    }
    follow_up_tasks = [
        task
        for task in current_tasks
        if task.get("intent") in EMAIL_INTENTS and task.get("intent") != original_intent
    ]
    return [original_task, *follow_up_tasks]


def _classify(text: str) -> str:
    if text in {"stop", "halt", "thamo", "ruko", "থামো", "रुको"}:
        return "STOP"

    # Research requests are read-only and must be recognized before broad
    # calendar/email catch-alls. Keep this semantic rather than phrase-exact.
    if re.search(
        r"\b(?:research|market|competitor(?:s)?|competition|industry|sector|swot|trends?|analy[sz]e|analysis|compare)\b"
        r"|(?:शोध|बाज़ार|बाजार|प्रतियोगी|उद्योग|क्षेत्र|स्वॉट|विश्लेषण|तुलना|रुझान|अवसर|कमजोरी|खतरा)"
        r"|(?:গবেষণা|বাজার|প্রতিযোগী|শিল্প|খাত|সুযোগ|দুর্বলতা|হুমকি|বিশ্লেষণ|তুলনা|প্রবণতা)",
        text,
        re.IGNORECASE,
    ):
        if re.search(
            r"\b(?:swot|strengths?|weaknesses?|opportunities|threats?)\b"
            r"|(?:স্বট|শক্তি|দুর্বলতা|সুযোগ|হুমকি|स्वॉट|ताकत|कमजोरी|अवसर|खतरा)",
            text,
            re.IGNORECASE,
        ):
            return "SWOT_ANALYSIS"
        if re.search(
            r"\b(?:competitor(?:s)?|competition|compare)\b"
            r"|(?:प्रतियोगी|तुलना|প্রতিযোগী|তুলনা)",
            text,
            re.IGNORECASE,
        ):
            return "COMPETITOR_ANALYSIS"
        return "MARKET_RESEARCH"

    # Email commands take precedence when a subject or body mentions a meeting.
    if re.search(r"\b(?:email|mail|message)\b", text) and re.search(
        r"\b(?:draft|compose|write|reply|respond|send|mail|forward)\b", text
    ):
        if re.search(r"\bforward\b", text):
            return "FORWARD_EMAIL"
        if re.search(r"\b(?:send|mail)\b", text) or re.search(
            r"\bemail\s+(?:it|this|that|the)\b", text
        ):
            if re.search(r"\b(?:to|recipient|address)\b", text):
                return "SEND_EMAIL"
            return "SEND_REPLY"
        if re.search(r"\b(?:reply|respond)\b", text):
            return "DRAFT_REPLY"
        return "COMPOSE_EMAIL"

    if _contains_any(text, ("cancel meeting", "বাতিল", "meeting cancel", "मीटिंग कैंसल")):
        return "CANCEL_MEETING"
    if _contains_any(text, ("reschedule", "পুনঃনির্ধারণ", "সময় বদল", "फिर से तय")):
        return "RESCHEDULE_MEETING"
    if (
        _contains_any(text, ("schedule meeting", "create meeting", "meeting with", "মিটিং তৈরি", "बैठक बन", "meeting banao"))
        or re.search(r"\b(?:schedule|create|book|arrange|set\s+up)\b.{0,40}\b(?:meeting|event|google\s+meet)\b", text)
    ):
        return "CREATE_MEETING"
    if re.search(r"\b(?:forward|forwarding)\b", text) and re.search(
        r"\b(?:email|mail|message|meeting\s+link|link)\b", text
    ):
        return "FORWARD_EMAIL"
    if re.search(r"\bforward\s+(?:it|this|that)\b", text):
        return "FORWARD_EMAIL"
    # This is an inbox search, not a calendar query: email contents can
    # mention meetings without asking about the user's schedule.
    # Broad: any sentence containing both email nouns and meeting keywords is
    # about the inbox, not the user's calendar — regardless of action verb.
    if (
        re.search(r"\b(?:emails?|mail|messages?)\b", text)
        and re.search(r"\b(?:meeting|meetings|calendar|schedule)\b", text)
        and not re.search(r"\b(?:schedule|create|book|arrange|set\s+up|cancel|reschedule)\b", text)
    ):
        return "CHECK_EMAIL"
    if _contains_any(text, ("available", "availability", "ফাঁকা", "उपलब्ध", "khali")):
        return "CHECK_AVAILABILITY"
    if _contains_any(text, ("tomorrow", "আগামীকাল", "कल")) and _contains_any(text, ("meeting", "calendar", "schedule", "মিটিং", "बैठक")):
        return "GET_TOMORROW_SCHEDULE"
    if _contains_any(text, ("today", "aaj", "আজ", "आज")) and _contains_any(text, ("meeting", "meetings", "calendar", "schedule", "মিটিং", "बैठक")):
        return "GET_TODAY_SCHEDULE"

    if re.search(r"\b(?:show|list|find|check)\s+(?:my\s+)?sent\s+(?:emails?|mail|messages?)\b", text):
        return "LIST_SENT_EMAILS"
    if re.search(r"\b(?:show|list|find|check)\s+(?:my\s+)?drafts?\b", text):
        return "LIST_DRAFT_EMAILS"
    if re.search(r"\b(?:show|list|find|check)\s+(?:my\s+)?(?:starred|favourite|favorite)\s+(?:emails?|mail|messages?)\b", text):
        return "LIST_STARRED_EMAILS"
    if re.search(r"\b(?:mark|make|set)\s+(?:the\s+)?(?:email|message|it)\s+(?:as\s+)?read\b", text):
        return "MARK_READ"
    if re.search(r"\b(?:mark|make|set)\s+(?:the\s+)?(?:email|message|it)\s+(?:as\s+)?unread\b", text):
        return "MARK_UNREAD"
    if re.search(r"\b(?:unstar|remove\s+star|unfavorite|unfavourite)\b", text):
        return "UNSTAR_EMAIL"
    if re.search(r"\b(?:star|favorite|favourite)\s+(?:the\s+)?(?:email|message|it)\b", text):
        return "STAR_EMAIL"
    if re.search(r"\barchive\s+(?:the\s+)?(?:email|message|it)\b", text):
        return "ARCHIVE_EMAIL"
    if re.search(r"\b(?:move|put)\s+(?:the\s+)?(?:email|message|it)\s+(?:to\s+)?trash\b", text):
        return "TRASH_EMAIL"
    if re.search(r"\b(?:permanently\s+)?delete\s+(?:the\s+)?(?:email|message|it)\b", text):
        return "DELETE_EMAIL"

    if (
        _contains_any(text, ("send reply", "reply send", "উত্তর পাঠাও", "जवाब भेज"))
        or re.search(r"\b(?:send|mail|email)\s+(?:it|this|that|the\s+(?:draft|reply|email))\b", text, re.IGNORECASE)
        or (
            re.search(r"\b(?:not|don'?t|don't(?:\s+uh)?)[^.]*?(?:make|keep)?\s*(?:it\s+)?(?:a\s+)?draft\b", text, re.IGNORECASE)
            and re.search(r"\b(?:send|mail|email|write)\b", text, re.IGNORECASE)
        )
    ):
        return "SEND_REPLY"
    if re.search(
        r"\b(?:send|sent|mail)\s+(?:an?\s+)?(?:new\s+)?(?:email|mail|message)\s+to\b",
        text,
    ):
        return "SEND_EMAIL"
    if (
        _contains_any(text, ("draft reply", "write reply", "উত্তর লিখ", "जवाब लिख"))
        or re.search(r"\b(?:reply|respond)\b", text)
    ):
        return "DRAFT_REPLY"
    if re.search(
        r"\b(?:draft|compose|write|create)\s+(?:an?\s+)?(?:new\s+)?(?:email|mail|message)\b",
        text,
    ):
        return "COMPOSE_EMAIL"
    if _contains_any(text, ("compose email", "write email", "নতুন ইমেইল", "ईमेल लिख")):
        return "COMPOSE_EMAIL"
    if _contains_any(text, ("urgent email", "important email", "জরুরি ইমেইল", "গুরুত্বপূর্ণ ইমেইল", "ज़रूरी ईमेल", "important emails")):
        return "GET_URGENT_EMAILS"
    if _contains_any(text, ("summarize thread", "thread summary")):
        return "SUMMARIZE_THREAD"
    if _contains_any(text, ("summarize email", "email summary", "ইমেইল সারাংশ", "ईमेल सारांश")):
        return "SUMMARIZE_EMAIL"
    if _contains_any(text, ("unread email", "unread emails", "অপঠিত ইমেইল", "बिना पढ़े ईमेल")):
        return "READ_UNREAD_EMAILS"
    if _contains_any(text, ("find email", "search email", "ইমেইল খুঁজ", "ईमेल खोज")):
        return "FIND_EMAIL"
    if _contains_any(text, ("read email", "ইমেইল পড়", "ईमेल पढ़")):
        return "READ_EMAIL"
    if _contains_any(text, ("email", "emails", "ইমেইল", "ईमेल")):
        return "CHECK_EMAIL"

    # Bengali/Hindi script commands that do not contain the English noun still
    # route deterministically before the calendar catch-all.
    if any(
        token in text
        for token in (
            "\u0987\u09ae\u09c7\u09b2",
            "\u0987\u09ae\u09c7\u0987\u09b2",
            "\u09ae\u09c7\u0987\u09b2",
            "\u09ac\u09be\u09b0\u09cd\u09a4\u09be",
            "\u0908\u092e\u0947\u0932",
            "\u092e\u0947\u0932",
            "\u0938\u0902\u0926\u0947\u0936",
        )
    ):
        return "CHECK_EMAIL"
    if any(
        token in text
        for token in (
            "\u0995\u09cd\u09af\u09be\u09b2\u09c7\u09a8\u09cd\u09a1\u09be\u09b0",
            "\u09ae\u09bf\u099f\u09bf\u0982",
            "\u09ac\u09c8\u09a0\u0995",
            "\u0995\u09c8\u09b2\u09c7\u0902\u0921\u0930",
            "\u092e\u0940\u091f\u093f\u0902\u0917",
            "\u092c\u0948\u0920\u0915",
        )
    ):
        return "CHECK_CALENDAR"

    # Calendar catch-all: only fires after all email rules have been exhausted,
    # preventing "meeting" from hijacking email-related queries.
    if _contains_any(text, ("calendar", "schedule", "meetings", "meeting", "ক্যালেন্ডার", "মিটিং", "कैलेंडर", "बैठक")):
        return "CHECK_CALENDAR"

    if (
        _contains_any(text, ("daily briefing", "morning briefing", "today's briefing", "todays briefing", "today briefing", "briefing for today", "দিনের ব্রিফিং", "दैनिक ब्रीफिंग"))
        or re.search(r"\bbriefing\b", text) and re.search(r"\b(?:today|daily|morning|দিন|दैनिक)\b", text)
    ):
        return "DAILY_BRIEFING"

    if _contains_any(text, ("move forward", "go forward", "এগিয়ে", "आगे")):
        return "MOVE_FORWARD"
    if _contains_any(text, ("move backward", "go back", "পিছিয়ে", "पीछे")):
        return "MOVE_BACKWARD"
    if _contains_any(text, ("turn left", "বামে ঘোর", "बाएं मुड़")):
        return "TURN_LEFT"
    if _contains_any(text, ("turn right", "ডানে ঘোর", "दाएं मुड़")):
        return "TURN_RIGHT"
    if _contains_any(text, ("come here", "কাছে আস", "यहाँ आ")):
        return "COME_HERE"
    if _contains_any(text, ("look at me", "look at user", "আমার দিকে তাকাও", "मेरी तरफ देख")):
        return "LOOK_AT_USER"
    if _contains_any(text, ("robot status", "status", "অবস্থা", "स्थिति")):
        return "STATUS"

    if _contains_any(text, ("help", "সাহায্য", "मदद")):
        return "HELP"
    if text:
        return "GENERAL_QUERY"
    return "UNKNOWN"


def _extract_entities(text: str) -> dict[str, Any]:
    entities: dict[str, Any] = {"source": text}
    time_match = re.search(
        r"\b(?:at\s+|@\s*)(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)\b",
        text,
    )
    if not time_match:
        time_match = re.search(
            r"\b(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?))\b",
            text,
        )
    if time_match:
        candidate = time_match.group(1).replace(".", "").strip()
        if int(re.match(r"\d+", candidate).group()) <= 23:
            entities["time"] = candidate
    if re.search(r"\b(tomorrow|আগামীকাল|कल)\b", text):
        entities["date"] = "tomorrow"
    elif re.search(r"\b(today|aaj|আজ|आज)\b", text):
        entities["date"] = "today"
    else:
        weekday_match = re.search(
            r"\b((?:next\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
            text,
        )
        if weekday_match:
            entities["date"] = weekday_match.group(1)

    email_address = _extract_email_address(text)
    if email_address:
        entities["participant_email"] = email_address

    subject_match = re.search(
        r"\bsubject(?:\s+(?:is|line|of))?\s*[:,-]?\s*(.+?)"
        r"(?=\s+(?:saying|that\s+says|with\s+(?:the\s+)?body|body\s+is|message\s+is)\b|$)",
        text,
    )
    if subject_match:
        subject = subject_match.group(1).strip(" \t\r\n,.:;\"'")
        if subject:
            entities["subject"] = subject

    topic_match = re.search(
        r"\b(?:topic|title)\s+(?:is|will\s+be)?\s*(?:about\s+)?(.+?)(?=\s+(?:today|tomorrow|on|at)\b|$)",
        text,
    )
    if topic_match:
        title = topic_match.group(1).strip(" \t\r\n,.:;\"'")
        if title:
            entities["title"] = title

    quoted_body_match = re.search(r"[\"“](.+?)[\"”]\s*$", text)
    body_match = re.search(
        r"\b(?:saying|that\s+says|with\s+(?:the\s+)?body|body\s+is|message\s+is)"
        r"\s*[:,-]?\s*(.+)$",
        text,
    )
    if quoted_body_match or body_match:
        body = (quoted_body_match or body_match).group(1).strip(" \t\r\n\"'“”")
        if body:
            entities["body"] = body
    elif email_address:
        email_details = _extract_email_address_details(text)
        trailing_text = text[email_details[1] :].strip(" \t\r\n,.:;-\"'“”") if email_details else ""
        if trailing_text and not re.match(r"^(?:with\s+)?subject\b", trailing_text):
            entities["body"] = trailing_text

    person_match = re.search(
        r"\bwith\s+(?!subject\b|(?:the\s+)?body\b)(.+?)"
        r"(?=\s+(?:today|tomorrow|on|at|@)\b|\s+[\w.+-]+@[\w.-]+\.[a-z]{2,}|$)",
        text,
    )
    if person_match:
        participant = person_match.group(1).strip(" ,.-")
        if participant:
            entities["participant"] = participant

    event_match = re.search(
        r"\b(?:cancel|reschedule)\s+(?:the\s+)?(?:meeting|event)?\s*(?:with\s+)?(.+?)(?=\s+(?:today|tomorrow|on|at|to)\b|$)",
        text,
    )
    if event_match and event_match.group(1).strip():
        entities["event_query"] = event_match.group(1).strip(" ,.-")

    email_query = re.search(r"\b(?:find|search)\s+(?:for\s+)?(?:an?\s+)?email\s*(?:from|about)?\s*(.+)$", text)
    if email_query and email_query.group(1).strip():
        entities["email_query"] = email_query.group(1).strip()

    event_reference_match = re.search(
        r"\b(?:meeting\s+link|join\s+(?:the\s+)?meeting|created\s+(?:the\s+)?meeting|new\s+meeting)\b",
        text,
    )
    if event_reference_match:
        entities["event_reference"] = event_reference_match.group(0)

    reply_query = re.search(r"\b(?:reply|respond)\s+(?:to\s+)?(?:the\s+)?(.+)$", text)
    if reply_query:
        candidate = re.sub(r"\s+(?:email|message)$", "", reply_query.group(1)).strip(" ,.-")
        generic_references = {
            "",
            "email",
            "message",
            "it",
            "this",
            "that",
            "recent",
            "latest",
            "last",
            "first",
            "second",
            "third",
        }
        if candidate not in generic_references:
            entities["email_query"] = candidate

    duration_match = re.search(r"\b(\d{1,3})\s*[- ]?\s*(?:minute|min)\b", text)
    if duration_match:
        entities["duration_minutes"] = int(duration_match.group(1))
    return entities


def _deterministic_task_plan(text: str) -> list[dict[str, Any]]:
    """Conservatively split explicit multi-step commands for offline fallback."""

    parts = [
        part.strip(" ,.")
        for part in re.split(r"\b(?:and then|then|after that|next)\b|[;\n]+", text)
        if part.strip(" ,.")
    ]
    if len(parts) == 1 and " and " in text:
        candidates = [part.strip(" ,.") for part in text.split(" and ") if part.strip(" ,.")]
        candidate_intents = [_classify(part) for part in candidates]
        if len(candidates) > 1 and all(
            intent not in {"GENERAL_QUERY", "UNKNOWN"} for intent in candidate_intents
        ) and not all(intent in MARKET_RESEARCH_INTENTS for intent in candidate_intents):
            parts = candidates

    tasks = []
    for part in parts[:4]:
        intent = _classify(part)
        tasks.append(
            {
                "intent": intent,
                "entities": _extract_entities(part),
                "description": part,
            }
        )
    return tasks or [
        {"intent": "UNKNOWN", "entities": {"source": text}, "description": text}
    ]


def _should_use_gemini(text: str, tasks: list[dict[str, Any]]) -> bool:
    if not gemini_reasoning_service.configured():
        return False
    if len(tasks) > 1:
        return True
    intent = tasks[0].get("intent") if tasks else "UNKNOWN"
    if intent in _GEMINI_ASSISTED_INTENTS:
        return True
    return bool(
        re.search(
            r"\b(?:first|second|third|this|that|it|same|organize|handle|follow up)\b",
            text,
        )
    )


def intent_node(state: AetherBotState) -> AetherBotState:
    """Create a typed specialist task plan with deterministic safe fallback."""

    text = state.get("normalized_input") or ""
    deterministic_tasks = _deterministic_task_plan(text)
    tasks = deterministic_tasks
    supervisor_mode = "deterministic"
    clarification = None

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

    clarification_context = state.get("clarification_context")
    continued_tasks = _continue_clarification(text, state, deterministic_tasks)
    if continued_tasks:
        tasks = continued_tasks
        supervisor_mode = "deterministic"
        clarification = None

    existing_entities = dict(state.get("entities") or {})
    for task_index, task in enumerate(tasks):
        task["entities"] = {**existing_entities, **dict(task.get("entities") or {})}
        task = _apply_current_draft_follow_up(task, text, state)
        task_text = str(task.get("description") or text).casefold()
        if re.search(r"\bforward\b", task_text) and re.search(
            r"\b(?:email|mail|message|meeting\s+link|link)\b", task_text
        ):
            task["intent"] = "FORWARD_EMAIL"
        if task.get("intent") in {"CREATE_MEETING", "RESCHEDULE_MEETING"} and not task["entities"].get("time"):
            clarification_context = {
                "intent": task.get("intent"),
                "entities": dict(task["entities"]),
                "description": task.get("description") or text,
                "input_source": state.get("input_source"),
            }
            task["intent"] = "GENERAL_QUERY"
            clarification = clarification or "What date and time should I use for the meeting?"
        if task.get("intent") == "COMPOSE_EMAIL" and not task["entities"].get("participant_email"):
            clarification_context = {
                "intent": task.get("intent"),
                "entities": dict(task["entities"]),
                "description": task.get("description") or text,
                "input_source": state.get("input_source"),
            }
            task["intent"] = "GENERAL_QUERY"
            clarification = clarification or "What email address should I draft this email to?"
        if task.get("intent") == "SEND_EMAIL" and not task["entities"].get("participant_email"):
            clarification_context = {
                "intent": task.get("intent"),
                "entities": dict(task["entities"]),
                "description": task.get("description") or text,
                "input_source": state.get("input_source"),
            }
            task["intent"] = "GENERAL_QUERY"
            clarification = clarification or "What email address should I send this email to?"
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
            task["intent"] = "GENERAL_QUERY"
            clarification = clarification or (
                "Which email should I send this reply to? Open or name the email, draft the reply, "
                "then ask me to mail it."
            )
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
    }


def route_by_intent(state: AetherBotState) -> str:
    """Map classified intents to a modular subgraph."""

    intent = state.get("intent") or "UNKNOWN"
    if intent in EMAIL_INTENTS:
        return "email"
    if intent in CALENDAR_INTENTS:
        return "calendar"
    if intent == "DAILY_BRIEFING":
        return "briefing"
    if intent in ROBOT_INTENTS:
        return "robot"
    return "assistant"
