# ElaraX

## What This Is

ElaraX is a local multilingual executive assistant for a personal command center. It combines a React/Vinext frontend, a FastAPI backend, and a LangGraph workflow that can read Gmail and Calendar context, draft messages, prepare calendar changes, handle voice commands, produce daily briefings, and simulate desk-robot commands.

The product is intentionally safety-first: AI can classify, plan, summarize, draft, transcribe, and speak, but it does not directly execute consequential actions. Email sends, calendar mutations, and robot movement stay behind deterministic confirmation gates.

## Core Value

Safely understand and act on local executive-assistant commands while keeping every consequential external or physical-world action under explicit human control.

## Requirements

### Validated

- ElaraX runs locally with the frontend at `http://localhost:3000` and API documentation at `http://localhost:8000/docs`.
- The root launcher `start.ps1` starts both `python -m uvicorn backend.api:app --reload --port 8000` and the frontend `npm run dev`.
- The FastAPI backend exposes health, overview, chat, confirmation, voice transcription, voice synthesis, Google OAuth, and invoice automation endpoints in `backend/api.py`.
- The master LangGraph in `backend/graphs/master_graph.py` routes each request through emergency stop, language detection, normalization, context resolution, intent planning, deterministic policy, a specialist subgraph, task collection, and final response normalization.
- Deterministic policy in `backend/nodes/policy_node.py` assigns risk and confirmation requirements; an LLM cannot override this node.
- Consequential email and calendar actions are prepared as pending actions and are executed only by `/api/confirm`.
- Google integrations default to mock services until a real local OAuth connection is available.
- Google OAuth credentials are loaded from ignored local files, and saved tokens are encrypted before being written to `data/`.
- Voice input supports hosted Groq STT first, Gemini transcription second, and local Whisper as the final fallback.
- The frontend supports typed text commands, manual microphone recording, "Hey Elara" wake phrase handling, Google connection controls, invoice auto-reply controls, spoken responses, and a demo fallback when the local API is unavailable.
- Backend tests cover API routes, graph routing, node behavior, Google auth, invoice automation, Gemini planning, and transcription provider ordering.
- Frontend Node-native tests cover wake phrase matching and wake-listener queue/stream helpers.
- A live local OAuth round trip is now verified: the dashboard reconnects to Google and renders real Gmail/Calendar-backed state.

### Active

- [ ] Keep this planning context synchronized with the codebase as the app changes.
- [ ] Resolve the remaining human-verification items in `.planning/debug/`, especially live voice-command latency/accuracy.
- [ ] Decide whether the repository root should become the canonical Git repository, because the root is not currently a Git repo while `frontend/` contains its own `.git`.
- [ ] Keep safety gates intact while adding or changing assistant capabilities.

### Out of Scope

- Bypassing confirmation for email sends, calendar writes, or robot movement - this would violate the central safety model.
- Direct physical robot hardware control from Gemini or any LLM - robot actions currently go through a simulator boundary.
- Committing `.env`, `secrets/`, encrypted Google tokens, generated local runtime state, or credential values - these are local-only by design.
- Multi-user production auth, hosted deployment hardening, or OAuth verification - current code is shaped around a single local user.
- Replacing LangGraph with direct model/tool execution - project rules require LangGraph as the primary orchestrator.

## Context

- The project root is `C:\Users\hazra\Downloads\desk_bot`.
- The public product name is ElaraX. Some older debug notes and comments refer to AetherBot or DeskRobo; treat those as historical names unless code still imports `aetherbot` identifiers.
- `README.md` is the current setup guide and documents Groq, Gemini, Google OAuth, voice commands, invoice auto-replies, and local run commands.
- `agents.txt` defines engineering rules: LangGraph first, Gemini as reasoning only, external integrations in services/tools, no direct LLM motor control, confirmation for consequential actions, and emergency STOP bypassing Gemini.
- `.planning/debug/` contains project memory from previous investigations:
  - `google-oauth-blank-popup.md` is resolved by launching Google OAuth in the system browser.
  - `google-oauth-org-internal.md` is awaiting a Google Cloud audience/test-user change.
  - `hey-elara-wake-command-not-working.md` records wake-listener fixes and remaining human verification.
  - `stt-transcription-inaccurate.md` contains useful voice-history notes but appears stale in one respect: it discusses an OpenAI STT provider, while current code and README use Groq first.
- The running app was verified locally on 2026-09-04: `http://localhost:3000` and `http://localhost:8000/docs` both responded successfully.

## Constraints

- **Local-first execution**: The UI only calls the backend when loaded from `localhost` or `127.0.0.1`; otherwise it falls back to demo data.
- **Safety policy**: `backend/nodes/policy_node.py` is the authority for risk and confirmation. Do not let model output bypass it.
- **Google OAuth**: Real Gmail and Calendar require a Web application OAuth client with redirect URI `http://localhost:8000/api/v1/auth/google/callback`.
- **Google scopes**: The app requests Gmail read/compose and Calendar events/freebusy scopes, so External Testing users and verification limits matter.
- **Secrets**: `.env`, `secrets/`, and `data/` are ignored. Documentation should name secret locations and environment variables without copying values.
- **Runtime**: The frontend declares Node `>=22.13.0`; this machine currently has Node `v25.8.2`. Python currently reports `3.10.11`, while `agents.txt` says Python `3.11+`.
- **State**: Pending confirmations are stored in backend memory, so they do not survive a backend restart.
- **Testing**: `pytest.ini` disables the asyncio plugin and limits Python tests to `backend/tests`.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use LangGraph as the primary workflow engine | Keeps routing, specialist workflows, state, and safety policy explicit | Good |
| Keep Gemini behind a reasoning-only service boundary | Allows planning, summarization, drafting, TTS, and transcription without direct execution authority | Good |
| Use deterministic confirmation for consequential actions | Prevents email, calendar, and robot writes from happening without user approval | Good |
| Launch Google OAuth in the system browser | Google blocks embedded browser OAuth flows | Good |
| Default to mock services until Google is connected | Keeps local development usable and safe without credentials | Good |
| Use hosted STT before local Whisper | Local Whisper works but can be slow on CPU-only machines | Good, keep provider docs current |
| Keep invoice auto-replies fixed-template and narrow | Reduces risk of overpromising payment approval or sending repeated replies | Good |
| Create root-level planning context without initializing root Git | User asked for context, not repository setup; root Git ownership is still unresolved | Pending |

---
*Last updated: 2026-09-05 after live backend/frontend smoke verification*
