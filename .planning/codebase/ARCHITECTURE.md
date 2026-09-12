# Architecture

## System Shape

ElaraX is organized as a local frontend plus local backend:

```text
Browser UI at localhost:3000
  -> typed helper functions in frontend/app/lib/aether-api.ts
  -> FastAPI in backend/api.py at localhost:8000
  -> LangGraph master graph in backend/graphs/master_graph.py
  -> specialist graph or service boundary
  -> mock services or real external providers
```

The frontend owns presentation, browser microphone behavior, wake phrase lifecycle, conversation UI state, and demo fallback. The backend owns all authoritative assistant behavior, service selection, external API access, policy, pending confirmations, OAuth, voice transcription, TTS, and invoice automation.

## Backend HTTP Boundary

`backend/api.py` defines the API surface and Pydantic request/response models.

Core routes:

- `GET /api/health` - backend readiness, graph mode, Google/simulation mode, Gemini/deterministic reasoning mode.
- `GET /api/overview` - urgent emails, today/tomorrow events, robot status, Google status, and provider name.
- `POST /api/chat` - creates or continues a conversation thread and invokes the master LangGraph.
- `POST /api/confirm` - approves or rejects one pending consequential action.
- `POST /api/voice/transcribe` - validates base64 audio and MIME type, then delegates to the transcription service.
- `POST /api/voice/synthesize` - delegates text-to-speech to Gemini.
- `GET /api/v1/auth/google/status` - reports Google OAuth readiness and connection state.
- `GET /api/v1/auth/google/start` - returns a Google authorization URL.
- `POST /api/v1/auth/google/launch` - opens Google auth in the system browser with local-header protection.
- `GET /api/v1/auth/google/callback` - completes OAuth and writes encrypted token state.
- `POST /api/v1/auth/google/disconnect` - revokes and clears the Google token.
- `GET /api/automation/invoice` - returns invoice auto-reply status.
- `PUT /api/automation/invoice` - enables or pauses invoice auto-replies.

Backend CORS allows local frontend origins and one deployed ChatGPT-site origin.

## LangGraph Flow

`backend/graphs/master_graph.py` composes the full request flow:

```text
emergency_guard
  -> language
  -> normalize
  -> context
  -> classify_intent
  -> classify_policy
  -> email | calendar | briefing | robot | assistant
  -> collect_task_result
  -> classify_policy again for next task, or finalize_response
```

Important properties:

- `emergency_guard` can route STOP directly to the robot graph before language or Gemini planning.
- `language` and `normalize` are deterministic.
- `context` resolves references such as "the second email", "that meeting", or "reply to it" against previous state.
- `classify_intent` uses deterministic classification first and only asks Gemini for supported complex cases.
- `classify_policy` is deterministic and assigns risk/confirmation.
- `collect_task_result` supports up to four ordered specialist tasks and stops early if any task produces an error or pending action.
- The compiled graph uses a memory checkpointer from `backend/graphs/graph_config.py`.

## Shared State

`backend/graphs/state.py` defines `AetherBotState`, a `TypedDict(total=False)` that lets each node return only the fields it owns.

Major state groups:

- Conversation: `thread_id`, `user_id`, `messages`
- Input/language: `raw_input`, `normalized_input`, `input_language`, `response_language`
- Intent/planning: `intent`, `intent_confidence`, `entities`, `supervisor_mode`, `task_queue`, `task_index`, `task_results`
- Context memory: active email and calendar event IDs
- Retrieved data: `retrieved_emails`, `calendar_events`
- Email drafting: `email_summary`, `email_analysis`, `reply_draft`, `reply_draft_email_id`
- Safety: `pending_action`, `risk_level`, `requires_confirmation`, `confirmation_status`
- Robot: `robot_command`, `robot_status`
- Output: `tool_results`, `final_response`, `error`

## Specialist Graphs

Email:

- Builder: `backend/graphs/email/graph.py`
- State: `backend/graphs/email/state.py`
- Router: `backend/graphs/email/routes.py`
- Nodes: `backend/graphs/email/nodes.py`
- Flow: route action -> fetch emails -> summarize/draft/respond -> end.
- Handles inbox queries, targeted reads, summaries, drafts, replies, new email drafts, and pending sends.

Calendar:

- Builder: `backend/graphs/calendar/graph.py`
- State: `backend/graphs/calendar/state.py`
- Nodes: `backend/graphs/calendar/nodes.py`
- Flow: perform action -> response -> end.
- Handles schedule reads, availability/conflict checks, and pending calendar mutations.

Briefing:

- Builder: `backend/graphs/briefing/graph.py`
- Nodes: `backend/graphs/briefing/nodes.py`
- Flow: load sources -> briefing response -> end.
- Aggregates important emails and today's calendar events.

Robot:

- Builder: `backend/graphs/robot/graph.py`
- Nodes: `backend/graphs/robot/nodes.py`
- Flow: prepare command -> robot policy -> robot response -> end.
- STOP and status execute immediately in simulation; movement commands become pending actions.

Assistant:

- Builder: `backend/graphs/assistant/graph.py`
- Nodes: `backend/graphs/assistant/nodes.py`
- Flow: assistant response -> end.
- Handles help, clarifications, and general answers through Gemini when available.

## Confirmation Flow

Consequential work is split into two phases:

1. `POST /api/chat` routes and prepares an action.
2. `POST /api/confirm` executes or rejects the prepared action.

Pending actions are stored in `_pending_actions` inside `backend/api.py`, keyed by conversation thread ID. The pending store is protected by `_pending_lock` but is process-local memory, so pending actions are lost on backend restart.

Actions executed by `/api/confirm`:

- `SEND_REPLY`
- `SEND_EMAIL`
- `CREATE_MEETING`
- `RESCHEDULE_MEETING`
- `CANCEL_MEETING`
- `ROBOT_COMMAND`

Mock-mode guardrails:

- Email sends and calendar writes are rejected in mock mode unless `AETHERBOT_TESTING=1`.
- Robot commands execute only through `backend/services/mock_robot_service.py`.

## Frontend Architecture

`frontend/app/page.tsx` is a single large client component. It owns:

- Conversation input and message list.
- Pending confirmation UI.
- Overview, Google status, and invoice automation cards.
- Voice recording and wake phrase state machines.
- TTS playback and browser fallback.
- Google connection/disconnection handlers.
- Invoice auto-reply enable/pause flow.
- Responsive command-center layout.

`frontend/app/lib/aether-api.ts` is the typed API facade:

- Calls local backend only when the page is running on `localhost` or `127.0.0.1`.
- Returns demo fixtures when the backend is unavailable for overview/chat/confirm flows.
- Requires the local backend for voice transcription, TTS, Google connection, and invoice automation.

## Voice Architecture

Manual voice:

```text
MediaRecorder in frontend/app/page.tsx
  -> transcribeVoice() in frontend/app/lib/aether-api.ts
  -> POST /api/voice/transcribe
  -> VoiceTranscriptionService
  -> Groq, then Gemini, then local Whisper
  -> submit transcript as chat command
```

Wake phrase:

- Browser speech recognition is used when available.
- `frontend/app/lib/wake-phrase.ts` accepts "Hey Elara", "Hey ElaraX", and the observed ASR rendering "Hey Alana".
- Browser recognition failures such as `network`, `service-not-allowed`, and `language-not-supported` trigger recorder fallback.
- `frontend/app/lib/wake-listener.ts` helps reuse live audio streams and serialize background clip transcription.

Spoken responses:

- Backend Gemini TTS is tried first through `/api/voice/synthesize`.
- Browser `speechSynthesis` is the fallback.

## Invoice Automation Architecture

Files:

- `backend/services/invoice_automation_service.py`
- `backend/api.py`
- `frontend/app/page.tsx`

Lifecycle:

- FastAPI lifespan starts `InvoiceAutomationWorker` unless `AETHERBOT_TESTING=1`.
- The worker loops until stopped, running `InvoiceAutomationService.run_once()` every configured interval.
- Enabling automation wakes the worker immediately.

Safety design:

- The reply body is fixed.
- Only unread invoice-like Gmail threads newer than 14 days are considered.
- No-reply, automated, list-unsubscribe, overdue, payment reminder, and final notice messages are skipped.
- Processed thread IDs are persisted locally to prevent duplicate acknowledgements.
- Reply count and recent replies are stored in the local settings file.

## Data Flow Boundaries

Data from email messages and user speech is treated as untrusted. Prompts explicitly tell Gemini not to follow instructions embedded in email content or generated responses.

Execution authority stays in deterministic code:

- `backend/nodes/policy_node.py`
- `backend/api.py` `/api/confirm`
- `backend/services/gmail_service.py`
- `backend/services/google_calendar_service.py`
- `backend/services/mock_robot_service.py`
