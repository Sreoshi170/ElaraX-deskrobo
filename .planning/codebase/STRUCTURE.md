# Structure

## Root

```text
.
├── README.md
├── requirements.txt
├── pytest.ini
├── start.ps1
├── agents.txt
├── .env.example
├── .gitignore
├── backend/
├── frontend/
├── data/
├── secrets/
└── .planning/
```

Important root files:

- `README.md` - primary setup, run, voice, Google, and invoice automation documentation.
- `requirements.txt` - Python backend/test dependencies.
- `pytest.ini` - backend test discovery and pytest plugin configuration.
- `start.ps1` - starts backend and frontend as hidden processes.
- `agents.txt` - local engineering rules and safety constraints.
- `.env.example` - environment variable reference without credentials.
- `.gitignore` - ignores Python caches, `.venv`, `.env*`, `secrets/`, and `data/`.

## Planning

Existing planning files before this context pass:

```text
.planning/
└── debug/
    ├── google-oauth-blank-popup.md
    ├── google-oauth-org-internal.md
    ├── hey-elara-wake-command-not-working.md
    └── stt-transcription-inaccurate.md
```

Context files created by this pass:

```text
.planning/
├── PROJECT.md
└── codebase/
    ├── ARCHITECTURE.md
    ├── CONCERNS.md
    ├── CONVENTIONS.md
    ├── INTEGRATIONS.md
    ├── STACK.md
    ├── STRUCTURE.md
    └── TESTING.md
```

## Backend

```text
backend/
├── __init__.py
├── api.py
├── config.py
├── graphs/
├── nodes/
├── services/
└── tests/
```

Backend root:

- `backend/api.py` - API app and endpoint implementation.
- `backend/config.py` - environment and path configuration.

Graphs:

```text
backend/graphs/
├── __init__.py
├── graph_config.py
├── master_graph.py
├── state.py
├── assistant/
├── briefing/
├── calendar/
├── email/
└── robot/
```

Shared graph files:

- `backend/graphs/state.py` - shared `AetherBotState`.
- `backend/graphs/graph_config.py` - memory checkpointer and thread config.
- `backend/graphs/master_graph.py` - top-level graph builder.

Specialist graph pattern:

- `backend/graphs/<domain>/graph.py` - builds a compiled subgraph.
- `backend/graphs/<domain>/nodes.py` - domain node logic.
- `backend/graphs/<domain>/state.py` - domain-specific state extension when needed.
- `backend/graphs/email/routes.py` - email-specific router.

Shared nodes:

```text
backend/nodes/
├── confirmation_node.py
├── context_node.py
├── emergency_stop_node.py
├── intent_node.py
├── language_node.py
├── policy_node.py
├── response_node.py
└── supervisor_node.py
```

Services:

```text
backend/services/
├── gemini_reasoning_service.py
├── gmail_service.py
├── google_auth_service.py
├── google_calendar_service.py
├── integration_service.py
├── invoice_automation_service.py
├── mock_calendar_service.py
├── mock_email_service.py
├── mock_robot_service.py
└── transcription_service.py
```

Service responsibilities:

- Gemini reasoning/TTS/transcription fallback: `backend/services/gemini_reasoning_service.py`
- Groq/Gemini/Whisper STT orchestration: `backend/services/transcription_service.py`
- OAuth and encrypted token storage: `backend/services/google_auth_service.py`
- Gmail API boundary: `backend/services/gmail_service.py`
- Google Calendar API boundary: `backend/services/google_calendar_service.py`
- Mock/live service selection: `backend/services/integration_service.py`
- Invoice automation: `backend/services/invoice_automation_service.py`
- Mock services and fixtures: `backend/services/mock_*.py`

Backend tests:

```text
backend/tests/
├── conftest.py
├── test_api.py
├── test_gemini_reasoning_service.py
├── test_google_auth_service.py
├── test_invoice_automation.py
├── test_transcription_service.py
└── graphs/
    ├── test_master_graph.py
    ├── test_state_and_nodes.py
    └── test_subgraphs.py
```

## Frontend

```text
frontend/
├── package.json
├── package-lock.json
├── vite.config.ts
├── next.config.ts
├── tsconfig.json
├── eslint.config.mjs
├── app/
├── public/
└── tests/
```

Frontend app:

```text
frontend/app/
├── globals.css
├── layout.tsx
├── page.tsx
└── lib/
    ├── aether-api.ts
    ├── wake-listener.ts
    └── wake-phrase.ts
```

Important frontend files:

- `frontend/app/page.tsx` - main user experience and client-side state machine.
- `frontend/app/layout.tsx` - root layout, metadata, fonts.
- `frontend/app/globals.css` - styling.
- `frontend/app/lib/aether-api.ts` - typed local API and demo fallback.
- `frontend/app/lib/wake-phrase.ts` - wake phrase parsing/scoring.
- `frontend/app/lib/wake-listener.ts` - wake stream/queue helpers.

Frontend tests:

```text
frontend/tests/
├── wake-listener.test.mjs
└── wake-phrase.test.mjs
```

Generated frontend directories:

- `frontend/.next`
- `frontend/.vinext`
- `frontend/.wrangler`
- `frontend/dist`
- `frontend/node_modules`

## Git Layout

The project root is not currently a Git repository. `frontend/` contains a nested `.git` directory.

Implications:

- Root-level files such as `backend/`, `.planning/`, `README.md`, and `requirements.txt` are not tracked by the nested frontend repo.
- Frontend files may have a separate Git history from backend/root planning files.
- Before committing project-wide context or backend changes, decide whether to initialize root Git, keep frontend as the only repo, or restructure repository ownership.

## Naming Notes

Names in the codebase are mixed:

- Current product/documentation name: ElaraX.
- Older or internal identifiers: AetherBot, Aether, DeskRobo.
- Shared graph state type: `AetherBotState`.
- CSS/UI classes still use `aether-*` in places.

Do not rename these casually; many names are historical but still wired into code.
