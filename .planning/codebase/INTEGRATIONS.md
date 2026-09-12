# Integrations

## Integration Model

All external services are behind backend service boundaries. The frontend never calls Google, Gemini, Groq, Gmail, Calendar, or local Whisper directly; it calls the local FastAPI API.

The main selector is `backend/services/integration_service.py`:

- If Google is connected, `get_email_service()` returns `GmailService`.
- If Google is connected, `get_calendar_service()` returns `GoogleCalendarService`.
- Otherwise both return mock services backed by local fixtures.

## Google OAuth

Files:

- `backend/services/google_auth_service.py`
- `backend/api.py`
- `frontend/app/lib/aether-api.ts`
- `frontend/app/page.tsx`

Scopes requested:

- `openid`
- `https://www.googleapis.com/auth/userinfo.email`
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.compose`
- `https://www.googleapis.com/auth/calendar.events`
- `https://www.googleapis.com/auth/calendar.freebusy`

Local credential paths:

- OAuth client JSON: `secrets/google_oauth_client.json` by default.
- Token encryption key: `secrets/token_encryption.key` by default.
- Encrypted OAuth token: `data/google_token.enc` by default.

Important behavior:

- The OAuth client must be a Google Web application client.
- The redirect URI must include `http://localhost:8000/api/v1/auth/google/callback`.
- `GoogleAuthManager.begin_authorization()` generates the Google authorization URL.
- `/api/v1/auth/google/launch` opens that URL in the operating system browser, guarded by local-only headers.
- `/api/v1/auth/google/callback` stores credentials through `EncryptedTokenStore`.
- `/api/v1/auth/google/disconnect` revokes and clears the saved token.
- `EncryptedTokenStore` uses Fernet encryption and writes tokens atomically through a temporary file.

Known project memory:

- `.planning/debug/google-oauth-blank-popup.md` explains why embedded browser OAuth failed and why the system-browser launch endpoint exists.
- `.planning/debug/google-oauth-org-internal.md` explains the Google Cloud "Internal" audience problem for personal Gmail accounts.

## Gmail

Files:

- `backend/services/gmail_service.py`
- `backend/graphs/email/nodes.py`
- `backend/api.py`

Capabilities:

- Load account profile.
- List messages newer than 90 days.
- Filter unread, important, or query-matched messages.
- Fetch full message body for targeted read/summarize/reply flows.
- Send confirmed replies or new messages.

Safety boundaries:

- Gmail sends are only performed inside `/api/confirm`.
- If the selected service is mock and the app is not in tests, `/api/confirm` rejects real email sends with "Connect Google before sending a real email."
- Email text is treated as untrusted content in prompts.
- The service sanitizes reply headers before writing `In-Reply-To` or `References`.

## Google Calendar

Files:

- `backend/services/google_calendar_service.py`
- `backend/graphs/calendar/nodes.py`
- `backend/api.py`

Capabilities:

- List upcoming, today, or tomorrow events.
- Find free/busy conflicts before scheduling or rescheduling.
- Create events with Google Meet conference data.
- Reschedule events.
- Cancel events.

Safety boundaries:

- Calendar mutations are prepared as pending actions by the graph.
- Real create/reschedule/cancel operations are only performed inside `/api/confirm`.
- If the selected service is mock and the app is not in tests, `/api/confirm` rejects real calendar writes with "Connect Google before changing your real calendar."

Date/time behavior:

- Timezone defaults to `Asia/Kolkata` through `AETHERBOT_TIMEZONE`.
- Dates accept `today`, `tomorrow`, or ISO dates.
- Times accept forms like `4 PM` or `16:00`.
- Ambiguous early hours without `am`/`pm` are shifted to afternoon when `hour <= 7`.

## Gemini

Files:

- `backend/services/gemini_reasoning_service.py`
- `backend/nodes/intent_node.py`
- `backend/graphs/email/nodes.py`
- `backend/graphs/assistant/nodes.py`
- `backend/api.py`

Capabilities:

- Plan a user request into one to four typed specialist tasks.
- Generate email summaries.
- Draft email replies and new email bodies.
- Answer general assistant questions.
- Transcribe audio as a fallback provider.
- Synthesize assistant responses as mono 24 kHz WAV audio.

Safety boundaries:

- Gemini returns structured plans or text only.
- Gemini never calls Gmail, Calendar, robot, or other execution services directly.
- Gemini planning is optional; deterministic routing remains the fallback.
- If Gemini is unavailable, callers use deterministic responses or a safe unavailability message.

Configuration:

- `GEMINI_API_KEY` or `AETHERBOT_GEMINI_API_KEY`
- Fallback file: `secrets/gemini_api_key.txt`
- Reasoning model: `AETHERBOT_GEMINI_MODEL`
- Transcription model: `AETHERBOT_GEMINI_TRANSCRIPTION_MODEL`
- TTS model: `AETHERBOT_GEMINI_TTS_MODEL`
- TTS voice: `AETHERBOT_GEMINI_TTS_VOICE`
- Timeout: `AETHERBOT_GEMINI_TIMEOUT_MS`

## Groq Speech-To-Text

Files:

- `backend/services/transcription_service.py`
- `backend/api.py`
- `README.md`

Capability:

- Hosted short-command transcription through Groq's OpenAI-compatible audio transcription endpoint.

Configuration:

- `GROQ_API_KEY` or `AETHERBOT_GROQ_API_KEY`
- `GROQ_TRANSCRIPTION_MODEL`, defaulting to `whisper-large-v3`
- `GROQ_TRANSCRIPTION_TIMEOUT_SECONDS`
- `AETHERBOT_DISABLE_GROQ_STT`

Behavior:

- Groq is tried first when configured.
- It uses an ElaraX-specific prompt to preserve commands, names, numbers, email addresses, and English/Bengali/Hindi/code-mixed speech.
- Errors are sanitized into stable categories such as authentication rejected, rate limited, request too large, service unavailable, timeout, network failure, or invalid provider response.

## Local Whisper

Files:

- `backend/services/transcription_service.py`
- `requirements.txt`

Capability:

- CPU/GPU local transcription fallback using `openai-whisper`.

Configuration:

- `AETHERBOT_WHISPER_MODEL`
- `AETHERBOT_WHISPER_CACHE_DIR`
- `AETHERBOT_WHISPER_LANGUAGE`
- `AETHERBOT_WHISPER_ALLOW_DOWNLOAD`
- `AETHERBOT_DISABLE_LOCAL_WHISPER`

Behavior:

- Local Whisper is lazy-loaded to avoid backend startup cost.
- It checks for the Python package, `ffmpeg`, and a cached checkpoint unless downloads are allowed.
- Temporary audio files are created for transcription and removed afterward.
- It is the final fallback after Groq and Gemini.

## Browser APIs

Files:

- `frontend/app/page.tsx`
- `frontend/app/lib/wake-phrase.ts`
- `frontend/app/lib/wake-listener.ts`

Capabilities:

- `MediaRecorder` captures manual voice commands and wake fallback clips.
- Browser `SpeechRecognition` or `webkitSpeechRecognition` is used when available for wake listening.
- Browser speech synthesis is used as a fallback if backend Gemini TTS is unavailable.
- `window.confirm` is used before enabling invoice auto-replies and disconnecting Google.
- `window.postMessage` is used by the OAuth result page when an opener exists.

## Local Files and State

Ignored local inputs:

- `.env`
- `secrets/google_oauth_client.json`
- `secrets/gemini_api_key.txt`
- `secrets/token_encryption.key`
- `data/google_token.enc`

Generated local state:

- `data/invoice_automation.json` by default for invoice automation settings, processed thread IDs, reply counts, and recent replies.
- `frontend/.next`, `frontend/.vinext`, `frontend/.wrangler`, `frontend/dist`, and `frontend/node_modules`.

## Mock Services

Files:

- `backend/services/mock_email_service.py`
- `backend/services/mock_calendar_service.py`
- `backend/services/mock_robot_service.py`
- `backend/services/integration_service.py`

Purpose:

- Keep the command center usable without live Google credentials.
- Keep tests deterministic.
- Preserve safety boundaries while developing graph flows.

Do not remove mock services until equivalent live integration coverage exists.
