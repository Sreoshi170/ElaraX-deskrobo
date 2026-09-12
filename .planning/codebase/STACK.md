# Stack

## Summary

ElaraX is a local two-service app:

- Backend: Python FastAPI plus LangGraph, Google API clients, Gemini, Groq STT, and local Whisper fallback.
- Frontend: React 19 through Vinext/Next-style app routing, Vite, Cloudflare plugin tooling, Tailwind PostCSS, and TypeScript.
- Runtime entrypoint: root `start.ps1`, which starts the backend on port `8000` and frontend on port `3000`.

## Observed Runtime

- Current project path: `C:\Users\hazra\Downloads\desk_bot`
- Python observed locally: `Python 3.10.11`
- Node observed locally: `v25.8.2`
- Frontend engine requirement: Node `>=22.13.0` in `frontend/package.json`
- Frontend dependencies are already installed in `frontend/node_modules`

## Backend

Key files:

- `backend/api.py` - FastAPI app, route models, CORS, lifespan worker, chat/confirm/OAuth/voice/automation endpoints.
- `backend/config.py` - loads root `.env` and centralizes paths, provider model names, timeouts, Google paths, and Whisper settings.
- `backend/graphs/master_graph.py` - top-level LangGraph composition.
- `backend/graphs/*/graph.py` - specialist graph builders for email, calendar, briefing, robot, and general assistant.
- `backend/nodes/*.py` - shared graph nodes for emergency stop, language, context, intent, policy, supervisor task collection, confirmation, and final response.
- `backend/services/*.py` - mock and real external integration boundaries.

Backend dependencies from `requirements.txt`:

- `fastapi`, `uvicorn[standard]`
- `langgraph`, `langchain-core`
- `pydantic`
- `cryptography`
- `google-api-python-client`, `google-auth`, `google-auth-httplib2`, `google-auth-oauthlib`, `google-genai`
- `requests`
- `python-dotenv`
- `pytest`
- `openai-whisper`

## Frontend

Key files:

- `frontend/app/page.tsx` - main command-center UI and most client-side interaction logic.
- `frontend/app/lib/aether-api.ts` - typed frontend API boundary with demo fallback.
- `frontend/app/lib/wake-phrase.ts` - wake phrase parsing and transcript alternative scoring.
- `frontend/app/lib/wake-listener.ts` - small helpers for reusing wake streams and serializing wake clip transcription.
- `frontend/app/globals.css` - application styling.
- `frontend/vite.config.ts` - Vinext, OpenAI Sites, Tailwind, and Cloudflare/Vite configuration.
- `frontend/next.config.ts` - currently empty Next config.

Frontend scripts from `frontend/package.json`:

- `npm run dev` - runs `vinext dev`.
- `npm run build` - runs `vinext build`.
- `npm run start` - runs `vinext start`.
- `npm run lint` - runs ESLint while ignoring `dist` and `.next`.

Primary frontend dependencies:

- `next` `16.2.6`
- `react` `19.2.6`
- `react-dom` `19.2.6`
- `vinext` `1.0.0-beta.3`
- `vite` `8.0.13`
- `@cloudflare/vite-plugin`
- `@openai/sites-vite-plugin`
- `tailwindcss` and `@tailwindcss/postcss`
- TypeScript and React type packages

## Local Commands

Install backend dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start both services:

```powershell
.\start.ps1
```

Start backend only:

```powershell
python -m uvicorn backend.api:app --reload --port 8000
```

Start frontend only:

```powershell
cd frontend
npm run dev
```

Open:

- UI: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/health`

Verify:

```powershell
python -m pytest -q
cd frontend
npm run build
```

## Configuration

Root `.env` is loaded by `backend/config.py` before configuration constants are read. `.env.example` documents the supported settings without containing credentials.

Important environment variables:

- `GROQ_API_KEY`
- `GROQ_TRANSCRIPTION_MODEL`
- `GROQ_TRANSCRIPTION_TIMEOUT_SECONDS`
- `GEMINI_API_KEY`
- `AETHERBOT_GEMINI_MODEL`
- `AETHERBOT_GEMINI_TRANSCRIPTION_MODEL`
- `AETHERBOT_GEMINI_TTS_MODEL`
- `AETHERBOT_GEMINI_TTS_VOICE`
- `AETHERBOT_GOOGLE_CLIENT_FILE`
- `AETHERBOT_GOOGLE_REDIRECT_URI`
- `AETHERBOT_TOKEN_KEY_FILE`
- `AETHERBOT_FRONTEND_ORIGIN`
- `AETHERBOT_TIMEZONE`
- `AETHERBOT_WHISPER_MODEL`
- `AETHERBOT_WHISPER_LANGUAGE`
- `AETHERBOT_WHISPER_ALLOW_DOWNLOAD`
- `AETHERBOT_DISABLE_LOCAL_WHISPER`

Ignored local state:

- `.env`
- `.env.*` except `.env.example`
- `secrets/`
- `data/`
- Python caches
- `.venv/`

## Build/Hosting Tooling

`frontend/vite.config.ts` configures:

- `vinext()` for the app runtime.
- `sites()` from `@openai/sites-vite-plugin`.
- `cloudflare()` from `@cloudflare/vite-plugin`.
- Tailwind through PostCSS.
- Local Wrangler and Miniflare state paths under `.wrangler/`.

The app is primarily developed locally. Treat Cloudflare/OpenAI Sites config as frontend build/hosting tooling, not as the backend's production deployment story.
