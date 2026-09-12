# Concerns

## Root Repository Is Not Git-Tracked

Observation:

- `git status --short` from the project root fails because `C:\Users\hazra\Downloads\desk_bot` is not a Git repository.
- `frontend/` contains its own `.git` directory.

Why it matters:

- Backend, planning docs, root README, requirements, and secrets ignore rules are outside the frontend repo's Git history.
- GSD commit tooling expects a project-level Git repo, but this root currently has none.

Suggested resolution:

- Decide whether the root should be initialized as the canonical repo, whether the frontend nested repo should remain separate, or whether the project should be restructured.

## Runtime Version Mismatch

Observation:

- `agents.txt` says Python `3.11+`.
- The local runtime reports `Python 3.10.11`.

Why it matters:

- Current code appears compatible with Python 3.10 syntax, but documented engineering expectations say 3.11+.
- Future contributors may introduce 3.11-only features assuming the rule is enforced.

Suggested resolution:

- Either upgrade the local/backend runtime to Python 3.11+ or update `agents.txt` to the actual supported Python range after testing.

## Stale Voice Debug Note

Observation:

- `.planning/debug/stt-transcription-inaccurate.md` discusses an OpenAI STT provider and `gpt-4o-mini-transcribe`.
- Current `backend/services/transcription_service.py`, `.env.example`, and `README.md` use Groq first, Gemini second, and local Whisper last.

Why it matters:

- Future debugging could follow the wrong provider trail.

Suggested resolution:

- Update or append that debug note to clearly mark the OpenAI branch as historical/stale, or split current Groq provider state into a fresh debug note if voice issues continue.

## Hidden Process Launcher

Observation:

- `start.ps1` starts backend and frontend with `Start-Process -WindowStyle Hidden`.
- It prints URLs but does not record process IDs, log files, or stop instructions.

Why it matters:

- It is hard to inspect server output or stop exactly the processes started by the launcher.
- Stale hidden servers can make changes appear not to work.

Suggested resolution:

- Add optional local logging and PID output, or create separate `start-backend`, `start-frontend`, and `stop` helpers.

## Large Frontend Component

Observation:

- `frontend/app/page.tsx` is a large single client component handling layout, chat, Google, invoice automation, wake phrase, recording, TTS, and confirmation UI.

Why it matters:

- Voice and async state changes are easy to break because many lifecycle refs and UI states live together.
- Reuse and focused testing are harder than with smaller components/hooks.

Suggested resolution:

- Extract stable pieces gradually: API-driven data hooks, confirmation card, Google card, invoice automation card, conversation panel, voice recorder hook, wake listener hook, and TTS hook.

## Pending Actions Are Process-Local

Observation:

- `_pending_actions` in `backend/api.py` is an in-memory dictionary keyed by thread ID.

Why it matters:

- A backend restart clears pending confirmations.
- Hidden process restarts or reloads may invalidate a pending approval card in the UI.

Suggested resolution:

- For local-only use this may be acceptable. If reliability matters, persist pending actions in encrypted local storage with short expiry and action integrity checks.

## Google OAuth Still Has Human-Controlled Setup Risk

Observation:

- `.planning/debug/google-oauth-org-internal.md` is awaiting human verification.
- Gmail scopes include restricted scopes, and External Testing requires test users and has token lifetime limits.

Why it matters:

- Code can be correct while Google still rejects sign-in because of Cloud Console configuration.
- Testing-mode refresh tokens may expire, requiring reconnects.

Suggested resolution:

- Keep a short Google setup checklist in README and update the debug note after successful personal-account OAuth.

## Voice Verification Depends On Live Environment

Observation:

- Wake phrase, microphone capture, hosted STT, Gemini TTS, local Whisper, `ffmpeg`, browser speech APIs, and provider quotas all affect the user-visible voice experience.

Why it matters:

- Unit tests cover parsing and provider ordering, but not end-to-end live microphone quality or provider latency.

Suggested resolution:

- Maintain a repeatable manual voice test script with expected transcript examples and measured latency targets.

## No Frontend Test Script

Observation:

- `frontend/tests/*.test.mjs` exists, but `frontend/package.json` does not define `npm test`.

Why it matters:

- Contributors may run only lint/build and miss wake helper regressions.

Suggested resolution:

- Add a package script such as `test: "node --test tests/*.test.mjs"` when changing frontend test tooling is in scope.

## Secrets Are Present Locally

Observation:

- The root contains ignored `secrets/`, `data/`, and `.env` files.

Why it matters:

- Documentation and debugging commands must avoid printing credential values.

Suggested resolution:

- Continue to read `.env.example` for variable names and inspect secret file existence/metadata only when needed.

## Name Drift

Observation:

- Current docs use ElaraX.
- Older debug notes and code identifiers include AetherBot, Aether, and DeskRobo.

Why it matters:

- Search and onboarding can be confusing.
- Renaming all identifiers would be risky without tests.

Suggested resolution:

- Treat name cleanup as a deliberate refactor, not incidental doc cleanup.
