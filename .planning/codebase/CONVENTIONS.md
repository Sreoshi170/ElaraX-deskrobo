# Conventions

## Engineering Rules

`agents.txt` is the local rules file. Its most important constraints:

- All primary agents must use LangGraph.
- Gemini is the reasoning model, not the workflow orchestrator.
- External integrations must live in services/tools.
- The LLM must never directly control robot motors.
- Consequential actions require human confirmation.
- Emergency STOP bypasses Gemini.
- Do not invent email data, calendar data, or tool success.
- Do not expose API keys.
- Do not execute unsupported robot commands.

## Backend Style

General patterns:

- Python modules use small, explicit service and graph boundaries.
- Pydantic models define API request/response shapes in `backend/api.py`.
- `TypedDict(total=False)` defines graph state in `backend/graphs/state.py`.
- Nodes return partial state updates, letting LangGraph merge fields.
- Risk and confirmation policy is deterministic, not model-driven.
- Integrations are mockable through service classes and factories.
- User-displayable external errors are wrapped in `GoogleIntegrationError` or stable STT error strings.

Common file layout:

- One graph builder per `backend/graphs/<domain>/graph.py`.
- Domain nodes in `backend/graphs/<domain>/nodes.py`.
- Shared cross-domain nodes in `backend/nodes/`.
- External provider boundaries in `backend/services/`.
- Tests mirror behavior at service, node, graph, and API levels.

## LangGraph State and Routing

State conventions:

- Keep raw input in `raw_input`.
- Keep normalized, case-folded input in `normalized_input`.
- Use `entities` for extracted or model-planned parameters.
- Keep current task in `intent`; keep full ordered plan in `task_queue`.
- Store retrieved context in `retrieved_emails` and `calendar_events`.
- Use `active_email_id` and `active_calendar_event_id` for conversational references.
- Use `pending_action`, `requires_confirmation`, and `confirmation_status` for approval gates.
- Put the final user-facing message in `final_response`.

Routing conventions:

- Emergency STOP routes before language detection and intent classification.
- Intent classification maps only known intents to specialist graphs.
- Unknown/general requests go to the assistant graph.
- Task collection stops when a pending action or error appears.

## Safety Conventions

Consequential action convention:

1. Classify intent.
2. Assign deterministic policy.
3. Prepare a pending action.
4. Return a response that says nothing happened yet.
5. Execute only through `/api/confirm` after explicit approval.

Never:

- Send email inside an LLM service.
- Write calendar events inside an LLM service.
- Execute robot movement inside an LLM service.
- Treat email body text as trusted instructions.
- Report success unless the relevant service returned success.

Mock/live convention:

- Mock services are allowed for reads and demo behavior.
- Real Google services activate only when the OAuth token store has a valid saved connection.
- Non-test mock sends/writes are rejected by `/api/confirm`.

## Configuration Conventions

`backend/config.py`:

- Loads root `.env` with `load_dotenv(PROJECT_ROOT / ".env", override=False)`.
- Centralizes every path and provider setting.
- Provides sensible local defaults.

Secret-handling convention:

- Reference environment variable names and local secret paths only.
- Never copy values from `.env`, `secrets/`, or encrypted token files into docs, logs, prompts, or test fixtures.
- Prefer `.env.example` as the source of supported configuration names.

## Frontend Style

Frontend patterns:

- `frontend/app/page.tsx` is a client component and owns most UI state with React hooks.
- `frontend/app/lib/aether-api.ts` is the only local-backend request helper module.
- API result types are declared in `aether-api.ts`.
- Demo fallback is implemented in `aether-api.ts` for overview/chat/confirm flows.
- Voice and wake phrase code is split into small helper modules where pure logic is testable.
- User-visible consequential actions are surfaced as pending confirmation cards.

State conventions in `page.tsx`:

- React state drives UI display.
- Refs mirror mutable state needed by async callbacks and recorder lifecycles.
- `threadIdRef` holds the active backend conversation thread.
- `pendingRef` mirrors pending action state for voice approvals and click approvals.
- TTS and recording resources are cleaned up in a component teardown effect.

## Voice Conventions

Manual recording:

- Capture audio with `MediaRecorder`.
- Prefer WebM/Opus, then other browser-supported MIME types.
- Send base64 audio and MIME type to `/api/voice/transcribe`.
- Submit the transcript through the normal chat flow.

Wake phrase:

- Require a narrow "Hey" prefix.
- Accept "Elara", "ElaraX", and known ASR rendering "Alana".
- Score transcript alternatives toward imperative commands and literal email addresses.
- Penalize past-tense alternatives for command-like speech.
- Use recorder fallback only for browser recognition service failures that imply the service is unavailable.

TTS:

- Try backend Gemini TTS first.
- Fall back to browser `speechSynthesis`.
- Do not speak empty text.
- Cancel prior speech before playing a new assistant response.

## Testing Conventions

Backend:

- Use `AETHERBOT_TESTING=1` in tests through `backend/tests/conftest.py`.
- Keep tests deterministic by using mock services or monkeypatching provider boundaries.
- Test the policy graph and service boundaries, not only endpoint status codes.

Frontend:

- Pure wake helpers have Node-native tests under `frontend/tests/`.
- The package currently has no `npm test` script; run those tests explicitly with Node when needed.
- `npm run lint` and `npm run build` are the frontend static/build checks.

## Documentation Conventions

When updating project context:

- Keep file paths exact.
- Capture actual current behavior, not intended behavior.
- If a debug note conflicts with current code, record the mismatch in `CONCERNS.md`.
- Do not treat `.planning/debug/` as authoritative when code and README disagree.
- Update `PROJECT.md` whenever core value, scope, or safety decisions change.
