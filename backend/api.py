"""HTTP API exposing ElaraX and the local Google OAuth connection."""

import base64
import binascii
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
import html
import json
import logging
import os
import re
import webbrowser
from contextlib import asynccontextmanager
from threading import Lock
from typing import Any, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.config import (
    FRONTEND_ORIGIN,
    OPENROUTER_API_KEY,
    TAVILY_API_KEY,
    WILI_API_KEY,
    WILI_BASE_URL,
)
from backend.graphs.graph_config import graph_run_config
from backend.graphs.master_graph import aetherbot_graph
from backend.nodes.intent_node import _extract_email_address
from backend.nodes.language_node import normalize_language_preference
from backend.services import integration_service
from backend.services.gmail_service import GmailService
from backend.services.google_auth_service import GoogleIntegrationError, google_auth_manager
from backend.services.gemini_reasoning_service import gemini_reasoning_service
from backend.services.localization_service import localization_service
from backend.services.transcription_service import voice_transcription_service
from backend.services.edge_tts_service import edge_tts_service
from backend.services.action_item_service import action_item_service
from backend.services.auth_service import (
    PROFILE_FIELDS,
    AuthError,
    authenticate,
    create_session_for_user,
    create_user,
    list_activity,
    record_activity,
    revoke_session,
    update_profile,
    user_from_token,
)
from backend.services.invoice_automation_service import (
    invoice_automation_service,
    invoice_automation_worker,
)
from backend.services.mock_robot_service import execute_mock_command, get_mock_status


logger = logging.getLogger("elarax.api")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2_000)
    thread_id: Optional[str] = None
    user_id: str = "local-user"
    input_source: Literal["typed", "voice"] = "typed"
    language: Literal["auto", "en", "bn", "hi", "mixed"] = "auto"


class ChatResponse(BaseModel):
    thread_id: str
    request_id: str = ""
    success: bool = True
    status: Literal["completed", "waiting_for_confirmation", "error"] = "completed"
    intent: str
    agent: str = "assistant"
    intent_confidence: float
    input_language: Optional[str] = None
    response_language: Optional[str] = None
    risk_level: Optional[str] = None
    requires_confirmation: bool = False
    pending_action: Optional[dict[str, Any]] = None
    response: str
    message: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    research_report: Optional[dict[str, Any]] = None
    emails: list[dict[str, Any]] = Field(default_factory=list)
    agent_mode: Literal["deterministic", "gemini"] = "deterministic"
    task_results: list[dict[str, Any]] = Field(default_factory=list)


class VoiceTranscriptionRequest(BaseModel):
    audio_base64: str = Field(min_length=4, max_length=8_000_000)
    mime_type: str = Field(min_length=5, max_length=100)
    language: Literal["auto", "en", "bn", "hi", "mixed"] = "auto"


class VoiceTranscriptionResponse(BaseModel):
    transcript: str


class VoiceSynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3_000)
    language: Optional[Literal["auto", "en", "bn", "hi", "mixed"]] = None


class VoiceSynthesisResponse(BaseModel):
    audio_base64: str
    mime_type: str


class ConfirmationRequest(BaseModel):
    thread_id: str
    decision: Literal["approve", "reject"]


class ConfirmationResponse(BaseModel):
    thread_id: str
    decision: Literal["approved", "rejected"]
    response: str
    result: Optional[dict[str, Any]] = None


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2_000)
    depth: Literal["quick", "standard", "deep"] = "standard"
    thread_id: Optional[str] = None
    language: Literal["auto", "en", "bn", "hi", "mixed"] = "auto"


class RobotCommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=40)
    parameters: dict[str, Any] = Field(default_factory=dict)


class GoogleConnectionStatus(BaseModel):
    configured: bool
    connected: bool
    email: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)
    expires_at: Optional[str] = None
    error: Optional[str] = None


class InvoiceAutomationSettingsRequest(BaseModel):
    enabled: bool


class InvoiceAutomationStatus(BaseModel):
    enabled: bool
    connected: bool
    poll_interval_seconds: int
    reply_template: str
    total_replies_sent: int
    last_run_at: Optional[str] = None
    last_error: Optional[str] = None
    recent_replies: list[dict[str, str]] = Field(default_factory=list)


class ActionItemRecord(BaseModel):
    id: str
    description: str
    due_date: Optional[str] = None
    source_email_id: str
    source_subject: str
    status: Literal["open", "done"]
    created_at: str


class ActionItemsResponse(BaseModel):
    items: list[ActionItemRecord] = Field(default_factory=list)


class ActionItemCompletionResponse(BaseModel):
    item: ActionItemRecord


class UserProfile(BaseModel):
    full_name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=5, max_length=254)
    phone: str = Field(default="", max_length=80)
    country: str = Field(default="", max_length=120)
    timezone: str = Field(default="Asia/Kolkata", max_length=120)
    occupation: str = Field(min_length=1, max_length=160)
    company_name: str = Field(min_length=1, max_length=200)
    website: str = Field(default="", max_length=400)
    industry: str = Field(min_length=1, max_length=160)
    company_size: str = Field(default="", max_length=80)
    business_stage: str = Field(default="", max_length=120)
    business_model: str = Field(min_length=1, max_length=2_000)
    revenue_model: str = Field(default="", max_length=2_000)
    products_services: str = Field(default="", max_length=2_000)
    target_customers: str = Field(default="", max_length=2_000)
    goals: str = Field(default="", max_length=2_000)
    challenges: str = Field(default="", max_length=2_000)
    business_context: str = Field(min_length=1, max_length=2_000)


class SignUpRequest(UserProfile):
    password: str = Field(min_length=8, max_length=256)


class SignInRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=5, max_length=254)
    phone: str = Field(default="", max_length=80)
    country: str = Field(default="", max_length=120)
    timezone: str = Field(default="Asia/Kolkata", max_length=120)
    occupation: str = Field(min_length=1, max_length=160)
    company_name: str = Field(min_length=1, max_length=200)
    website: str = Field(default="", max_length=400)
    industry: str = Field(min_length=1, max_length=160)
    company_size: str = Field(default="", max_length=80)
    business_stage: str = Field(default="", max_length=120)
    business_model: str = Field(min_length=1, max_length=2_000)
    revenue_model: str = Field(default="", max_length=2_000)
    products_services: str = Field(default="", max_length=2_000)
    target_customers: str = Field(default="", max_length=2_000)
    goals: str = Field(default="", max_length=2_000)
    challenges: str = Field(default="", max_length=2_000)
    business_context: str = Field(min_length=1, max_length=2_000)


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: dict[str, Any]


def _profile_payload(model: BaseModel) -> dict[str, Any]:
    values = model.model_dump()
    return {field: values.get(field, "") for field in PROFILE_FIELDS}


def _bearer_user(authorization: str, *, required: bool = False) -> dict[str, Any] | None:
    # Some endpoints call `chat` internally instead of through FastAPI's
    # dependency injection, so its Header default can arrive as a Header
    # instance rather than a string.
    if not isinstance(authorization, str) or not authorization:
        if required:
            raise HTTPException(status_code=401, detail="Sign in to continue.")
        return None
    scheme, _, token = authorization.partition(" ")
    user = user_from_token(token.strip()) if scheme.casefold() == "bearer" else None
    if not user:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    return user


def _record_activity_safely(
    user_id: str | None,
    activity_type: str,
    title: str,
    detail: str = "",
    status: str = "completed",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Keep dashboard telemetry best-effort so it can never break an agent turn."""

    if not user_id:
        return
    try:
        record_activity(user_id, activity_type, title, detail, status, metadata)
    except Exception:  # pragma: no cover - telemetry must not affect core work
        logger.exception("Could not record dashboard activity")


@asynccontextmanager
async def _app_lifespan(_: FastAPI):
    if os.getenv("AETHERBOT_TESTING") != "1":
        invoice_automation_worker.start()
    try:
        yield
    finally:
        invoice_automation_worker.stop()


app = FastAPI(
    title="ElaraX API",
    version="0.1.0",
    description="A safe HTTP boundary around the hybrid Gemini + LangGraph ElaraX assistant.",
    lifespan=_app_lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://aetherbot-command-center.sreoshibhowmik28.chatgpt.site",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_graph_lock = Lock()
_pending_lock = Lock()
_pending_actions: dict[str, dict[str, Any]] = {}
_EMAIL_CONFIRMATION_ACTIONS = {
    "SEND_REPLY",
    "SEND_EMAIL",
    "FORWARD_EMAIL",
    "MARK_READ",
    "MARK_UNREAD",
    "STAR_EMAIL",
    "UNSTAR_EMAIL",
    "ARCHIVE_EMAIL",
    "TRASH_EMAIL",
    "DELETE_EMAIL",
}


def _verified_source_recipient(email_service: Any, details: dict[str, Any]) -> str:
    """Return the source email's reply address, refusing guessed or changed recipients."""

    source_email_id = str(details.get("source_email_id") or "").strip()
    getter = getattr(email_service, "get_email", None)
    source_email = getter(source_email_id) if getter and source_email_id else {}
    source_value = str((source_email or {}).get("reply_to") or (source_email or {}).get("sender") or "").strip()
    requested_value = str(details.get("participant_email") or "").strip()
    _, source_address = parseaddr(source_value)
    _, requested_address = parseaddr(requested_value)
    source_address = source_address.strip()
    requested_address = requested_address.strip()
    valid_addresses = all(
        address.count("@") == 1
        and all(part.strip() for part in address.split("@", 1))
        and "." in address.rsplit("@", 1)[-1]
        and not any(character.isspace() for character in address)
        for address in (source_address, requested_address)
    )
    if not valid_addresses or requested_address.casefold() != source_address.casefold():
        logger.warning(
            "Refusing auto meeting reply because the recipient did not match source email %s",
            source_email_id or "<missing>",
        )
        raise GoogleIntegrationError(
            "I could not verify the meeting reply recipient from the source email. "
            "No event or reply was created; please confirm the recipient."
        )
    return source_address


def _is_recipient_correction(message: str) -> bool:
    """Recognize a correction to a pending recipient without creating a new task."""

    lowered = message.casefold()
    return bool(
        # Original patterns
        re.search(r"\b(?:email|address|recipient)\s+(?:is\s+)?wrong\b", lowered)
        or re.search(r"\b(?:use|replace(?:\s+it)?\s+with)\s+(?:this|that|the)\b", lowered)
        # "wrong email/address" (reversed word order)
        or re.search(r"\bwrong\s+(?:email|address|recipient)\b", lowered)
        # "change/update/correct the recipient/address/email"
        or re.search(r"\b(?:change|update|correct|fix)\s+(?:the\s+)?(?:recipient|address|email)\b", lowered)
        # "no, send it to X instead" / "send to X instead"
        or re.search(r"\b(?:send|forward)\s+(?:it\s+)?to\b.*\binstead\b", lowered)
        # "actually the email/address is" / "it should be"
        or re.search(r"\b(?:actually|no)\b.*\b(?:email|address)\s+(?:is|should\s+be)\b", lowered)
        or re.search(r"\bit\s+should\s+be\b", lowered)
        # "not that one, use X" / "no that's wrong"
        or re.search(r"\b(?:no|not)\s+(?:that(?:'s|\s+is)?|the)\s+(?:wrong|right|correct)\b", lowered)
        or re.search(r"\bnot\s+that\s+(?:one|address|email)\b", lowered)
        # "use X@Y instead" / "use this address"
        or re.search(r"\buse\s+\S+@\S+", lowered)
        or re.search(r"\buse\s+(?:this|that)\s+(?:address|email)\b", lowered)
    )


def _known_addresses_for_thread(thread_id: str) -> set[str]:
    """Read source-backed addresses from the conversation checkpoint."""

    try:
        state = aetherbot_graph.get_state(graph_run_config(thread_id)).values
    except Exception:
        return set()
    addresses: set[str] = set()
    for email in state.get("retrieved_emails") or []:
        for value in (email.get("reply_to"), email.get("sender")):
            _, address = parseaddr(str(value or ""))
            if address and address.count("@") == 1:
                addresses.add(address.casefold())
    return addresses


def _localize_thread_message(thread_id: str, message: str) -> str:
    """Use the conversation's selected language for confirmation results."""

    try:
        language = aetherbot_graph.get_state(graph_run_config(thread_id)).values.get(
            "response_language"
        )
    except Exception:
        language = "en"
    return localization_service.localize_text(message, language)


def _apply_pending_recipient_correction(request: ChatRequest) -> ChatResponse | None:
    """Update only an existing pending recipient; never send or re-plan the request."""

    if not request.thread_id or not _is_recipient_correction(request.message):
        return None
    with _pending_lock:
        pending = _pending_actions.get(request.thread_id)
        if not pending:
            return None

        replacement = _extract_email_address(request.message.casefold())
        if not replacement:
            return ChatResponse(
                thread_id=request.thread_id,
                intent=str(pending.get("action") or "UNKNOWN"),
                intent_confidence=1.0,
                risk_level="CONSEQUENTIAL",
                requires_confirmation=True,
                pending_action=dict(pending),
                response="Which email address should replace the pending recipient? Please provide the full address.",
            )
        if request.input_source == "voice" and replacement.casefold() not in _known_addresses_for_thread(request.thread_id):
            return ChatResponse(
                thread_id=request.thread_id,
                intent=str(pending.get("action") or "UNKNOWN"),
                intent_confidence=1.0,
                risk_level="CONSEQUENTIAL",
                requires_confirmation=True,
                pending_action=dict(pending),
                response=(
                    "I could not verify that voice-dictated replacement address against a sender in your inbox. "
                    "Please type the address exactly before approving the action."
                ),
            )

        updated = dict(pending)
        if updated.get("recipient") is not None:
            updated["recipient"] = replacement
        else:
            details = dict(updated.get("details") or {})
            if "participant_email" not in details:
                return None
            details["participant_email"] = replacement
            updated["details"] = details
        _pending_actions[request.thread_id] = updated

    return ChatResponse(
        thread_id=request.thread_id,
        intent=str(updated.get("action") or "UNKNOWN"),
        intent_confidence=1.0,
        risk_level="CONSEQUENTIAL",
        requires_confirmation=True,
        pending_action=updated,
        response=f"Updated the pending recipient to {replacement}. The action is still waiting for your confirmation.",
    )


def _google_status() -> dict[str, Any]:
    summary = google_auth_manager.connection_summary()
    summary["configured"] = google_auth_manager.client_file.is_file()
    if summary.get("connected"):
        try:
            profile = GmailService().get_profile()
            summary["email"] = profile.get("emailAddress")
        except GoogleIntegrationError as exc:
            summary["error"] = str(exc)
    return summary


@app.post("/api/auth/signup", response_model=AuthResponse, status_code=201)
def auth_signup(request: SignUpRequest) -> AuthResponse:
    try:
        user = create_user(_profile_payload(request), request.password)
        token = create_session_for_user(user["id"])
    except AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _record_activity_safely(
        user["id"],
        "account",
        "Workspace created",
        f"Profile created for {user['profile'].get('company_name') or 'your business'}.",
    )
    return AuthResponse(access_token=token, user=user)


@app.post("/api/auth/signin", response_model=AuthResponse)
def auth_signin(request: SignInRequest) -> AuthResponse:
    try:
        token, user = authenticate(request.email, request.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _record_activity_safely(user["id"], "account", "Signed in", "A new workspace session was started.")
    return AuthResponse(access_token=token, user=user)


@app.get("/api/auth/me")
def auth_me(authorization: str = Header(default="")) -> dict[str, Any]:
    return _bearer_user(authorization, required=True) or {}


@app.put("/api/auth/profile")
def auth_profile(
    request: ProfileUpdateRequest,
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    user = _bearer_user(authorization, required=True)
    try:
        return update_profile(user["id"], _profile_payload(request))
    except AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/dashboard")
def dashboard(authorization: str = Header(default="")) -> dict[str, Any]:
    """Return the authenticated user's complete, refreshable workspace snapshot."""

    user = _bearer_user(authorization, required=True)
    overview_data = overview()
    action_items = action_item_service.list_items()
    invoice_status = invoice_automation_service.status()
    profile = user["profile"]
    completed_action_items = [item for item in action_items if item["status"] == "done"]
    open_action_items = [item for item in action_items if item["status"] == "open"]
    profile_fields_completed = sum(bool(profile.get(field)) for field in PROFILE_FIELDS)
    activity = list_activity(user["id"], limit=100)
    today = datetime.now(timezone.utc).date()
    activity_by_day: dict[str, int] = {}
    for record in activity:
        try:
            activity_date = datetime.fromisoformat(
                str(record["created_at"]).replace("Z", "+00:00")
            ).astimezone(timezone.utc).date()
        except (TypeError, ValueError, OverflowError):
            continue
        day_age = (today - activity_date).days
        if 0 <= day_age < 7:
            key = activity_date.isoformat()
            activity_by_day[key] = activity_by_day.get(key, 0) + 1
    tracked_days = [
        {
            "date": (today - timedelta(days=offset)).isoformat(),
            "count": activity_by_day.get(
                (today - timedelta(days=offset)).isoformat(), 0
            ),
        }
        for offset in range(6, -1, -1)
    ]
    total_action_items = len(action_items)
    action_completion = round(
        (len(completed_action_items) / total_action_items) * 100
    ) if total_action_items else 0
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "user": user,
        "overview": overview_data,
        "action_items": action_items,
        "activity": activity,
        "google": overview_data.get("google") or _google_status(),
        "invoice_automation": invoice_status,
        "health": health(),
        "owner_progress": {
            "profile_setup": round((profile_fields_completed / len(PROFILE_FIELDS)) * 100),
            "action_completion": action_completion,
            "activity_momentum": min(100, round((sum(day["count"] for day in tracked_days) / 7) * 100)),
            "active_days": sum(1 for day in tracked_days if day["count"]),
            "tracked_days": tracked_days,
            "goal": profile.get("goals") or "Define a clear business goal in your profile.",
            "current_challenge": profile.get("challenges") or "No current challenge recorded.",
            "next_action": open_action_items[0]["description"] if open_action_items else "Choose the next milestone for your business.",
        },
        "stats": {
            "open_action_items": len(open_action_items),
            "completed_action_items": len(completed_action_items),
            "urgent_emails": len(overview_data.get("urgent_emails") or []),
            "today_events": len(overview_data.get("today_events") or []),
            "tomorrow_events": len(overview_data.get("tomorrow_events") or []),
            "activity_count": len(activity),
            "profile_completion": round((profile_fields_completed / len(PROFILE_FIELDS)) * 100),
        },
    }


@app.post("/api/auth/signout")
def auth_signout(authorization: str = Header(default="")) -> dict[str, bool]:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.casefold() == "bearer":
            revoke_session(token.strip())
    return {"signed_out": True}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "graph": "ready",
        "mode": "google" if integration_service.google_is_connected() else "simulation",
        "reasoning": "gemini" if gemini_reasoning_service.configured() else "deterministic",
        "research_retrieval": (
            "wili"
            if WILI_API_KEY and WILI_BASE_URL
            else "tavily"
            if TAVILY_API_KEY
            else "duckduckgo"
        ),
        "research_analysis": "openrouter" if OPENROUTER_API_KEY else "retrieval_only",
    }


@app.get("/api/agents")
def list_agents() -> dict[str, Any]:
    """Describe the agents registered behind the central supervisor."""

    return {
        "agents": [
            {"id": "assistant", "name": "General Assistant", "read_only": True},
            {"id": "email", "name": "Email Agent", "read_only": False},
            {"id": "calendar", "name": "Calendar Agent", "read_only": False},
            {"id": "briefing", "name": "Briefing Agent", "read_only": True},
            {"id": "market_research", "name": "Market Research Agent", "read_only": True},
            {"id": "robot", "name": "Robot Agent", "read_only": False},
        ],
        "orchestrator": "supervisor",
    }


@app.get("/api/robot/status")
def robot_status() -> dict[str, Any]:
    return get_mock_status()


@app.post("/api/robot/command", response_model=ChatResponse)
def robot_command(request: RobotCommandRequest) -> ChatResponse:
    allowed = {
        "STOP": "stop",
        "MOVE_FORWARD": "move forward",
        "MOVE_BACKWARD": "move backward",
        "TURN_LEFT": "turn left",
        "TURN_RIGHT": "turn right",
        "COME_HERE": "come here",
        "LOOK_AT_USER": "look at me",
        "GET_STATUS": "robot status",
        "STATUS": "robot status",
    }
    command = request.command.strip().upper()
    if command not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported robot command.")
    return chat(
        ChatRequest(
            message=allowed[command],
            thread_id=None,
            input_source="typed",
        )
    )


@app.get("/api/v1/auth/google/status", response_model=GoogleConnectionStatus)
def google_status() -> GoogleConnectionStatus:
    return GoogleConnectionStatus(**_google_status())


@app.get("/api/automation/invoice", response_model=InvoiceAutomationStatus)
def invoice_automation_status() -> InvoiceAutomationStatus:
    return InvoiceAutomationStatus(**invoice_automation_service.status())


@app.put("/api/automation/invoice", response_model=InvoiceAutomationStatus)
def update_invoice_automation(request: InvoiceAutomationSettingsRequest) -> InvoiceAutomationStatus:
    try:
        status = invoice_automation_service.set_enabled(request.enabled)
    except GoogleIntegrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if request.enabled:
        invoice_automation_worker.wake()
    return InvoiceAutomationStatus(**status)


@app.get("/api/action-items", response_model=ActionItemsResponse)
def list_action_items(
    status: Optional[Literal["open", "done"]] = Query(default=None),
) -> ActionItemsResponse:
    return ActionItemsResponse(items=action_item_service.list_items(status=status))


@app.post("/api/action-items/{item_id}/complete", response_model=ActionItemCompletionResponse)
def complete_action_item(
    item_id: str,
    authorization: str = Header(default=""),
) -> ActionItemCompletionResponse:
    try:
        item = action_item_service.complete_item(item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="That action item no longer exists.") from exc
    user = _bearer_user(authorization)
    _record_activity_safely(
        user["id"] if user else None,
        "action",
        "Action item completed",
        item["description"],
        "completed",
        {"action_item_id": item["id"]},
    )
    return ActionItemCompletionResponse(item=item)


@app.post("/api/voice/transcribe", response_model=VoiceTranscriptionResponse)
def transcribe_voice(request: VoiceTranscriptionRequest) -> VoiceTranscriptionResponse:
    mime_type = request.mime_type.split(";", 1)[0].strip().casefold()
    allowed_mime_types = {
        "audio/wav",
        "audio/mp3",
        "audio/mpeg",
        "audio/aiff",
        "audio/aac",
        "audio/ogg",
        "audio/flac",
        "audio/m4a",
        "audio/mp4",
        "audio/opus",
        "audio/webm",
    }
    if mime_type not in allowed_mime_types:
        raise HTTPException(status_code=415, detail="This audio format is not supported.")
    try:
        audio_bytes = base64.b64decode(request.audio_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="The voice recording is not valid base64 audio.") from exc
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="The voice recording was empty.")
    if len(audio_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Keep voice commands under 5 MB.")
    preferred_language = normalize_language_preference(request.language)
    try:
        transcript = voice_transcription_service.transcribe_audio(
            audio_bytes,
            mime_type,
            preferred_language,
        )
    except TypeError:
        # Preserve compatibility with an injected legacy STT adapter.
        transcript = voice_transcription_service.transcribe_audio(audio_bytes, mime_type)
    if not transcript:
        provider_unavailable = (
            voice_transcription_service.last_error or ""
        ).startswith("TranscriptionUnavailable:")
        detail = (
            "Voice transcription is temporarily unavailable. Please try again in a moment."
            if provider_unavailable
            else "I could not understand that recording. Please try again."
        )
        raise HTTPException(status_code=503, detail=detail)
    return VoiceTranscriptionResponse(transcript=transcript[:2_000])


@app.post("/api/voice/synthesize", response_model=VoiceSynthesisResponse)
def synthesize_voice(request: VoiceSynthesisRequest) -> VoiceSynthesisResponse:
    try:
        audio_bytes = gemini_reasoning_service.synthesize_speech(request.text, request.language)
    except TypeError:
        # Preserve compatibility with injected test/dummy providers that still
        # implement the legacy one-argument method.
        audio_bytes = gemini_reasoning_service.synthesize_speech(request.text)
    mime_type = "audio/wav"
    if not audio_bytes:
        audio_bytes = edge_tts_service.synthesize_speech(request.text, request.language)
        mime_type = edge_tts_service.MIME_TYPE
    if not audio_bytes:
        raise HTTPException(status_code=503, detail="Spoken output is temporarily unavailable.")
    return VoiceSynthesisResponse(
        audio_base64=base64.b64encode(audio_bytes).decode("ascii"),
        mime_type=mime_type,
    )


@app.get("/api/v1/auth/google/start")
def google_auth_start() -> dict[str, str]:
    try:
        return {"authorization_url": google_auth_manager.begin_authorization()}
    except GoogleIntegrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/auth/google/launch")
def google_auth_launch(
    x_elarax_local: str = Header(default=""),
    x_aetherbot_local: str = Header(default=""),
) -> dict[str, bool]:
    """Open Google's consent screen in the machine's normal web browser.

    Google sign-in is intentionally handed off from embedded app browsers. The
    custom header forces a CORS preflight, so an unrelated website cannot make
    the local service open browser tabs without the approved local origin.
    """
    if x_elarax_local != "1" and x_aetherbot_local != "1":
        raise HTTPException(status_code=403, detail="Local ElaraX request required.")
    try:
        authorization_url = google_auth_manager.begin_authorization()
        print("\n\n=== ACTION REQUIRED ===")
        print("Please copy and paste this link into your browser to log in:")
        print(authorization_url)
        print("=======================\n\n")
        launched = webbrowser.open_new_tab(authorization_url)
    except GoogleIntegrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not launched:
        raise HTTPException(
            status_code=500,
            detail="Your system browser could not be opened. Check the default browser setting and try again.",
        )
    return {"launched": True}


def _oauth_result_page(success: bool, message: str) -> str:
    status = "connected" if success else "error"
    safe_message = html.escape(message)
    origin_json = json.dumps(FRONTEND_ORIGIN)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>ElaraX Google connection</title>
<style>body{{margin:0;background:#0b0f15;color:#f4f4f0;font:16px system-ui;display:grid;place-items:center;min-height:100vh}}main{{max-width:460px;padding:32px;border:1px solid #29313b;border-radius:18px;background:#12171f}}h1{{font-size:22px}}p{{color:#9aa3af;line-height:1.55}}a{{color:#c9f576}}</style></head>
<body><main><h1>{'Google connected' if success else 'Connection not completed'}</h1>
<p>{safe_message}</p><p><a href={origin_json}>Return to ElaraX</a></p></main>
<script>if(window.opener){{window.opener.postMessage({{type:'aetherbot-google-auth',status:'{status}'}},{origin_json});setTimeout(()=>window.close(),900);}}</script>
</body></html>"""


@app.get("/api/v1/auth/google/callback", response_class=HTMLResponse)
def google_auth_callback(request: Request, state: str = "", error: Optional[str] = None) -> HTMLResponse:
    if error:
        return HTMLResponse(
            _oauth_result_page(False, "Google access was cancelled or denied."), status_code=400
        )
    try:
        google_auth_manager.complete_authorization(state, str(request.url))
    except GoogleIntegrationError as exc:
        return HTMLResponse(_oauth_result_page(False, str(exc)), status_code=400)
    return HTMLResponse(
        _oauth_result_page(True, "Your Gmail and Google Calendar are ready in ElaraX.")
    )


@app.post("/api/v1/auth/google/disconnect", response_model=GoogleConnectionStatus)
def google_disconnect() -> GoogleConnectionStatus:
    google_auth_manager.revoke_and_clear()
    return GoogleConnectionStatus(
        configured=google_auth_manager.client_file.is_file(),
        connected=False,
        email=None,
        scopes=[],
    )


@app.get("/api/overview")
def overview() -> dict[str, Any]:
    email_service = integration_service.get_email_service()
    calendar_service = integration_service.get_calendar_service()
    integration_error: Optional[str] = None
    try:
        urgent = email_service.list_emails(max_results=8, important_only=True)
        today_events = calendar_service.list_events("today")
        tomorrow_events = calendar_service.list_events("tomorrow")
    except GoogleIntegrationError as exc:
        urgent = []
        today_events = []
        tomorrow_events = []
        integration_error = str(exc)
    return {
        "urgent_emails": urgent,
        "today_events": today_events,
        "tomorrow_events": tomorrow_events,
        "robot": get_mock_status(),
        "google": _google_status(),
        "provider": email_service.provider_name,
        "integration_error": integration_error,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    authorization: str = Header(default=""),
) -> ChatResponse:
    request_id = str(uuid4())
    thread_id = request.thread_id or str(uuid4())
    authenticated_user = _bearer_user(authorization)
    request_user_id = authenticated_user["id"] if authenticated_user else request.user_id
    correction = _apply_pending_recipient_correction(request)
    if correction is not None:
        return correction
    # Fault 6 safety net: if _is_recipient_correction didn't fire but there
    # IS a pending action with a recipient field and the user's message
    # contains an email address (and is short / looks corrective), treat it
    # as a correction rather than spawning a new task.
    with _pending_lock:
        pending = _pending_actions.get(thread_id)
    if pending and (pending.get("recipient") is not None or "participant_email" in (pending.get("details") or {})):
        replacement = _extract_email_address(request.message.casefold())
        if replacement and len(request.message.split()) <= 15:
            # Synthesize a corrective message so the existing handler applies
            synthetic = ChatRequest(
                message=f"use {replacement}",
                thread_id=request.thread_id,
                user_id=request.user_id,
                input_source=request.input_source,
                language=request.language,
            )
            correction = _apply_pending_recipient_correction(synthetic)
            if correction is not None:
                return correction
    clean_turn_state = {
        "thread_id": thread_id,
        "user_id": request_user_id,
        "raw_input": request.message,
        "input_source": request.input_source,
        "language_hint": request.language,
        "entities": {},
        "task_queue": [],
        "task_index": 0,
        "task_results": [],
        "supervisor_clarification": None,
        "supervisor_error": None,
        "detected_meeting_proposal": None,
        "detected_deadline": None,
        "bridged_meeting_email_ids": [],
        "bridged_deadline_email_ids": [],
        "pending_action": None,
        "confirmation_status": None,
        "requires_confirmation": False,
        "final_response": None,
        "error": None,
        "robot_command": None,
        "robot_status": None,
        "tool_results": {},
        "research_query": None,
        "research_status": None,
        "research_report": None,
        "research_result": None,
        "research_sources": [],
        "research_warnings": [],
        "sources": [],
        "swot": None,
    }
    try:
        with _graph_lock:
            result = aetherbot_graph.invoke(clean_turn_state, config=graph_run_config(thread_id))
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=500, detail="The assistant graph could not process the request.") from exc

    pending_action = result.get("pending_action")
    if pending_action:
        with _pending_lock:
            _pending_actions[thread_id] = dict(pending_action)
    else:
        with _pending_lock:
            _pending_actions.pop(thread_id, None)

    research_report = result.get("research_report") or result.get("research_result")
    sources = result.get("research_sources") or result.get("sources") or []
    selected_agent = str(result.get("current_agent") or "")
    if not selected_agent or selected_agent == "assistant":
        task_results = result.get("task_results") or []
        if task_results and task_results[-1].get("agent"):
            selected_agent = str(task_results[-1]["agent"])
        intent_agent = {
            "MARKET_RESEARCH": "market_research",
            "COMPETITOR_ANALYSIS": "market_research",
            "SWOT_ANALYSIS": "market_research",
            "STOP": "robot",
            "MOVE_FORWARD": "robot",
            "MOVE_BACKWARD": "robot",
            "TURN_LEFT": "robot",
            "TURN_RIGHT": "robot",
            "COME_HERE": "robot",
            "LOOK_AT_USER": "robot",
            "STATUS": "robot",
            "DAILY_BRIEFING": "briefing",
            "CHECK_CALENDAR": "calendar",
            "GET_TODAY_SCHEDULE": "calendar",
            "GET_TOMORROW_SCHEDULE": "calendar",
        }.get(str(result.get("intent") or ""))
        if intent_agent and (not selected_agent or selected_agent == "assistant"):
            selected_agent = intent_agent
    status = "waiting_for_confirmation" if pending_action else ("error" if result.get("error") else "completed")
    chat_response = ChatResponse(
        thread_id=thread_id,
        request_id=request_id,
        success=not bool(result.get("error")),
        status=status,
        intent=result.get("intent") or "UNKNOWN",
        agent=selected_agent,
        intent_confidence=float(result.get("intent_confidence") or 0.0),
        input_language=result.get("input_language"),
        response_language=result.get("response_language") or result.get("input_language"),
        risk_level=result.get("risk_level"),
        requires_confirmation=bool(result.get("requires_confirmation")),
        pending_action=pending_action,
        response=result.get("final_response") or "No response was produced.",
        message=result.get("final_response") or "No response was produced.",
        data={
            "research": research_report,
            "swot": result.get("swot"),
            "sources": sources,
            "robot": result.get("robot_status"),
        },
        sources=sources,
        research_report=research_report,
        agent_mode=result.get("supervisor_mode") or "deterministic",
        task_results=result.get("task_results") or [],
        emails=[
            {
                key: email.get(key)
                for key in (
                    "id",
                    "thread_id",
                    "sender",
                    "sender_name",
                    "subject",
                    "snippet",
                    "date",
                    "unread",
                    "urgent",
                )
            }
            for email in (result.get("retrieved_emails") or [])
        ],
    )
    if authenticated_user:
        _record_activity_safely(
            authenticated_user["id"],
            "assistant",
            f"{chat_response.intent.replace('_', ' ').title()} request",
            chat_response.response,
            chat_response.status,
            {
                "thread_id": chat_response.thread_id,
                "agent": chat_response.agent,
                "input_source": request.input_source,
                "risk_level": chat_response.risk_level,
            },
        )
    return chat_response


@app.post("/api/assistant/run", response_model=ChatResponse)
def assistant_run(request: ChatRequest) -> ChatResponse:
    return chat(request)


@app.post("/api/research", response_model=ChatResponse)
def research(request: ResearchRequest) -> ChatResponse:
    return chat(
        ChatRequest(
            message=request.query,
            thread_id=request.thread_id,
            input_source="typed",
            language=request.language,
        )
    )


@app.post("/api/confirm", response_model=ConfirmationResponse)
def confirm(request: ConfirmationRequest) -> ConfirmationResponse:
    with _pending_lock:
        pending = _pending_actions.get(request.thread_id)
    if pending is None:
        raise HTTPException(status_code=404, detail="No pending action exists for this conversation.")

    if request.decision == "reject":
        with _pending_lock:
            _pending_actions.pop(request.thread_id, None)
        return ConfirmationResponse(
            thread_id=request.thread_id,
            decision="rejected",
            response=_localize_thread_message(
                request.thread_id,
                "Action cancelled. Nothing was changed.",
            ),
        )

    action = pending.get("action")
    result: dict[str, Any]
    try:
        if action in _EMAIL_CONFIRMATION_ACTIONS:
            service = integration_service.get_email_service()
            if service.provider_name == "mock" and os.getenv("AETHERBOT_TESTING") != "1":
                raise GoogleIntegrationError("Connect Google before changing a real email.")
            if action == "SEND_EMAIL":
                result = service.send_email(pending)
                message = (
                    "Email sent successfully through Gmail."
                    if service.provider_name == "google"
                    else "Email approved in the test simulator."
                )
            elif action == "SEND_REPLY":
                result = service.send_reply(pending)
                message = (
                    "Reply sent successfully through Gmail."
                    if service.provider_name == "google"
                    else "Reply approved in the test simulator."
                )
            elif action == "FORWARD_EMAIL":
                result = service.forward_email(pending)
                message = (
                    "Email forwarded successfully through Gmail."
                    if service.provider_name == "google"
                    else "Forward approved in the test simulator."
                )
            else:
                operation = {
                    "MARK_READ": "mark_read",
                    "MARK_UNREAD": "mark_unread",
                    "STAR_EMAIL": "star_email",
                    "UNSTAR_EMAIL": "unstar_email",
                    "ARCHIVE_EMAIL": "archive_email",
                    "TRASH_EMAIL": "trash_email",
                    "DELETE_EMAIL": "delete_email",
                }[action]
                result = getattr(service, operation)(pending)
                message = {
                    "MARK_READ": "Email marked as read.",
                    "MARK_UNREAD": "Email marked as unread.",
                    "STAR_EMAIL": "Email starred.",
                    "UNSTAR_EMAIL": "Email unstarred.",
                    "ARCHIVE_EMAIL": "Email archived.",
                    "TRASH_EMAIL": "Email moved to trash.",
                    "DELETE_EMAIL": "Email permanently deleted.",
                }[action]
        elif action in {"CREATE_MEETING", "RESCHEDULE_MEETING", "CANCEL_MEETING"}:
            service = integration_service.get_calendar_service()
            if service.provider_name == "mock" and os.getenv("AETHERBOT_TESTING") != "1":
                raise GoogleIntegrationError("Connect Google before changing your real calendar.")
            details = dict(pending.get("details") or {})
            if service.provider_name == "mock":
                if action == "CREATE_MEETING" and details.get("auto_reply_with_link"):
                    raise GoogleIntegrationError(
                        "Connect Google before booking a deadline meeting and sending its Meet link."
                    )
                result = {"ok": True, "mock": True, "operation": action, "details": details}
                message = "Calendar action approved in the test simulator."
            elif action == "CREATE_MEETING":
                email_service = None
                verified_recipient = None
                if details.get("auto_reply_with_link"):
                    email_service = integration_service.get_email_service()
                    if email_service.provider_name == "mock" and os.getenv("AETHERBOT_TESTING") != "1":
                        raise GoogleIntegrationError(
                            "Connect Gmail before sending the deadline meeting reply."
                        )
                    # Verify before creating the event too, so a changed/guessed recipient
                    # cannot become an unintended Calendar attendee.
                    verified_recipient = _verified_source_recipient(email_service, details)
                    details["participant_email"] = verified_recipient
                calendar_result = service.create_event(details)
                if not calendar_result.get("ok", True) or not calendar_result.get("meet_link"):
                    raise GoogleIntegrationError(
                        "Google Calendar did not return a Meet link, so no reply was sent."
                    )
                if details.get("auto_reply_with_link"):
                    source_subject = str(details.get("source_subject") or details.get("title") or "Meeting request")
                    subject = source_subject if source_subject.casefold().startswith("re:") else f"Re: {source_subject}"
                    reply_result = email_service.send_reply(
                        {
                            "recipient": verified_recipient,
                            "subject": subject,
                            "draft": (
                                f"Thanks for reaching out. I scheduled our meeting for "
                                f"{details.get('date') or 'the agreed time'} at {details.get('time')}.\n\n"
                                f"Here is the Google Meet link: {calendar_result['meet_link']}"
                            ),
                            "thread_id": details.get("source_thread_id"),
                            "in_reply_to": details.get("source_message_id"),
                            "references": details.get("source_references"),
                            "source_email_id": details.get("source_email_id"),
                        }
                    )
                    result = {"calendar": calendar_result, "email": reply_result}
                    message = (
                        "Meeting created successfully in Google Calendar, and a reply with the "
                        "Google Meet link was sent."
                    )
                else:
                    result = calendar_result
                    message = "Meeting created successfully in Google Calendar."
            elif action == "RESCHEDULE_MEETING":
                result = service.reschedule_event(details)
                message = "Meeting rescheduled successfully in Google Calendar."
            else:
                result = service.cancel_event(details)
                message = "Meeting cancelled successfully in Google Calendar."
            try:
                with _graph_lock:
                    aetherbot_graph.update_state(
                        graph_run_config(request.thread_id),
                        {
                            "calendar_events": []
                            if action == "CANCEL_MEETING"
                            else [result.get("calendar", result)],
                            "active_calendar_event_id": None
                            if action == "CANCEL_MEETING"
                            else (result.get("calendar", result) or {}).get("id"),
                        },
                        as_node="finalize_response",
                    )
            except Exception:
                # The external Calendar action already succeeded; context refresh is best effort.
                pass
        elif action == "ROBOT_COMMAND":
            command = pending.get("command") or {}
            result = execute_mock_command(command)
            message = "Robot command approved and acknowledged by the simulator."
        else:
            result = {"ok": True, "mock": True, "operation": action}
            message = "Action approved in simulation."
    except GoogleIntegrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    with _pending_lock:
        _pending_actions.pop(request.thread_id, None)

    return ConfirmationResponse(
        thread_id=request.thread_id,
        decision="approved",
        response=_localize_thread_message(request.thread_id, message),
        result=result,
    )
