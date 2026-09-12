# Testing

## Test Commands

Backend:

```powershell
python -m pytest -q
```

Frontend build:

```powershell
cd frontend
npm run build
```

Frontend lint:

```powershell
cd frontend
npm run lint
```

Frontend wake helper tests:

```powershell
cd frontend
node --test tests/*.test.mjs
```

The frontend package currently does not define an `npm test` script.

## Backend Test Configuration

`pytest.ini`:

```ini
[pytest]
testpaths = backend/tests
addopts = -p no:asyncio
```

`backend/tests/conftest.py` sets `AETHERBOT_TESTING=1`, which prevents live provider behavior such as starting the invoice automation worker or treating saved Google tokens as connected state.

## Backend Test Coverage Map

API:

- `backend/tests/test_api.py`
- Covers health/overview, graph-backed chat routing, confirmation requirements, confirmed email send simulation, guarded Google launch, voice transcription validation, voice synthesis, and invoice automation status/update routes.

Graph and nodes:

- `backend/tests/graphs/test_master_graph.py`
- `backend/tests/graphs/test_state_and_nodes.py`
- `backend/tests/graphs/test_subgraphs.py`
- Covers routing for read requests, multi-step plans, contextual email references, email drafting/sending confirmation, robot confirmation, emergency stop, language detection, intent routing, policy assignment, email graph behavior, calendar mutation preparation, briefing aggregation, and robot simulation behavior.

Google auth:

- `backend/tests/test_google_auth_service.py`
- Covers encrypted token store round trip and OAuth authorization URL generation.

Invoice automation:

- `backend/tests/test_invoice_automation.py`
- Covers one receipt per invoice thread, duplicate prevention, inert behavior while disabled, and connection requirement before enabling.

Gemini reasoning:

- `backend/tests/test_gemini_reasoning_service.py`
- Covers typed specialist task planning, disabled Gemini behavior during tests, transcription fallback expectations, and avoiding repeated failed transcription model retries.

Transcription:

- `backend/tests/test_transcription_service.py`
- Covers Groq provider construction and key precedence, sanitized error mapping, local Whisper temp-file cleanup and lazy load behavior, provider ordering, Gemini fallback, and local Whisper final fallback.

## Frontend Test Coverage Map

Wake phrase:

- `frontend/tests/wake-phrase.test.mjs`
- Covers accepted wake names, rejected unrelated phrases, inline command extraction, recorder fallback error categories, and transcript alternative scoring.

Wake listener:

- `frontend/tests/wake-listener.test.mjs`
- Covers reusing only active streams with live tracks and serializing background wake clip work after successful or failed queue items.

## Manual Verification

Run locally:

```powershell
.\start.ps1
```

Verify:

- UI responds at `http://localhost:3000`.
- API docs respond at `http://localhost:8000/docs`.
- `GET http://localhost:8000/api/health` reports `status: ok`.
- The command box can answer read-only demo commands such as "Show urgent emails" when Google is not connected.
- Consequential commands such as "Schedule meeting with Rahul tomorrow at 4" create a pending confirmation instead of changing Google Calendar directly.
- "STOP" returns an emergency stop acknowledgement without asking Gemini or requiring confirmation.

Google manual checks:

- Place the OAuth Web client JSON at `secrets/google_oauth_client.json`.
- Ensure the Google Cloud project has the correct external/testing audience and the user's Gmail account is a test user when using restricted scopes in testing mode.
- Click Connect Google in the UI and complete the system-browser consent flow.
- Confirm `/api/v1/auth/google/status` reports connected.
- Verify reads before writes; send and calendar changes must still require confirmation.

Voice manual checks:

- Configure `GROQ_API_KEY` for fast hosted STT, or confirm Gemini/local Whisper fallback expectations.
- Restart the backend after changing credentials or environment.
- Use the manual microphone button and inspect the displayed transcript.
- Enable "Hey Elara" and test both "Hey Elara" and an inline command such as "Hey Elara, show urgent emails".
- Confirm spoken responses use Gemini TTS when available and browser speech synthesis as fallback.

Invoice automation manual checks:

- Connect Google first.
- Enable auto-replies from the UI.
- Confirm the warning/confirmation copy before enabling.
- Use test invoice email threads only.
- Verify no replies are sent to no-reply/list/automated senders and no overdue/payment-reminder acknowledgement is sent.

## Verification Risks

- The root is not a Git repo, so root-level test and doc changes are not currently captured by `git status` at the project root.
- `frontend/` is a nested Git repo, so frontend status must be checked from `frontend/` if source files there change.
- The active app can be running from hidden processes started by `start.ps1`; if a change seems stale, check port owners or restart explicitly.
- Voice behavior depends on live browser microphone permission, hosted provider credentials, quotas, and local `ffmpeg`/Whisper availability.
- Google OAuth behavior depends on user-controlled Google Cloud Console settings that cannot be fully verified from code alone.
