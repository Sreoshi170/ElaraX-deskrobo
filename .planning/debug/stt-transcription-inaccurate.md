---
status: awaiting_human_verify
trigger: "the stt is not working properly"
created: 2026-08-30T10:53:24.9375127+05:30
updated: 2026-08-30T12:43:00+05:30
---

## Current Focus

hypothesis: Confirmed and fixed: CPU-only local Whisper was accurate but too slow as the unconditional first provider; configured hosted OpenAI STT now short-circuits both fallbacks.
test: Add an OpenAI key, restart the backend, hard-refresh, and compare two real recorded voice commands against the former approximately seven-second local cold path.
expecting: The recording uses `gpt-4o-mini-transcribe`, returns noticeably faster than local CPU inference, and still preserves imperative verbs, recipient addresses, and message wording.
next_action: Await human verification with a real credential and microphone; no real hosted request is possible until the user supplies the key.

## Symptoms

expected: Microphone commands after “Hey Elara” should be captured fully and transcribed accurately enough to preserve imperative verbs, email addresses, quoted/message content, and natural pauses.
actual: The transcription endpoint returns text, but important words are misrecognized or unreliable; the user says STT is not working properly.
errors: No explicit API error reported. The failure appears to be inaccurate or incomplete text rather than a failed request.
reproduction: Open localhost:3000, enable Hey Elara or press the microphone, speak an email command such as “send an email to [address], I love you bubu”, then inspect the transcript displayed as the user message.
started: Current issue after recent wake-word and email-agent upgrades; whether STT was ever consistently accurate is unknown.

## Eliminated

- hypothesis: The manual recorder sends an unsupported codec or corrupts the base64 payload.
  evidence: WebM codec parameters are deliberately stripped only for MIME allow-listing; the original bytes are retained, short payload endpoint tests pass, and a valid in-memory WAV reached the provider boundary before receiving a quota error.
  timestamp: 2026-08-30T10:58:34.8812134+05:30

## Evidence

- timestamp: 2026-08-30T10:54:24.9591464+05:30
  checked: Primary Hey Elara SpeechRecognition flow in `frontend/app/page.tsx`.
  found: When a recognition result contains both the wake phrase and a command, `onresult` stores the browser transcript and `onend` sends it directly to `processVoiceTranscript`; no audio blob or `/api/voice/transcribe` call is involved.
  implication: The screenshot-style transcript can come entirely from Chrome's built-in recognizer, so improving Gemini's transcription prompt alone cannot fix inline wake commands.

- timestamp: 2026-08-30T10:54:24.9591464+05:30
  checked: Manual microphone recording and `/api/voice/transcribe` boundary.
  found: Manual capture records WebM/Opus in 250 ms chunks for up to 15 seconds; the API strips codec parameters, accepts WebM, validates base64 and size, and forwards the bytes to the configured Gemini transcription model.
  implication: No static MIME mismatch or payload truncation is present in the manual recorder-to-server path.

- timestamp: 2026-08-30T10:54:24.9591464+05:30
  checked: Compatible wake recorder flow.
  found: Compatible mode rotates fixed 4.5-second clips and transcribes each clip independently. A wake phrase and command crossing a clip boundary cannot be reconstructed because transcripts are not overlapped or combined.
  implication: Even where the server STT is used, long commands can be split or truncated at arbitrary clip boundaries.

- timestamp: 2026-08-30T10:58:34.8812134+05:30
  checked: Live server transcription using a valid in-memory WAV command.
  found: `/api/voice/transcribe` returned 503. A direct provider probe revealed `429 RESOURCE_EXHAUSTED` for `gemini-3.5-flash` (free-tier request limit); the service has no alternate model and masks the failure as generic unavailability.
  implication: Recorded voice commands currently fail outright whenever the dedicated transcription model quota is exhausted, even though the configured `gemini-3.5-flash-lite` reasoning model remains able to transcribe audio.

- timestamp: 2026-08-30T10:58:34.8812134+05:30
  checked: Controlled WAV against `gemini-3.5-flash-lite` with a command-specific transcription instruction.
  found: The fallback model returned a complete email command and preserved the imperative `send`; it also normalized spoken `at gmail dot com` to an email address. The uncommon username remained phonetic, which is an inherent ambiguity without spelling/contact hints.
  implication: Model fallback restores availability and a domain-specific prompt improves command structure, while confirmation remains necessary for consequential actions.

- timestamp: 2026-08-30T11:04:01.4441487+05:30
  checked: Focused backend and frontend regression verification after the fix.
  found: 15 backend transcription/API tests passed, 8 wake/voice tests passed, and frontend lint passed.
  implication: Failover, prompt constraints, alternative ranking, and provider-unavailability reporting are protected by automated tests.

- timestamp: 2026-08-30T11:04:01.4441487+05:30
  checked: Complete backend suite and production frontend compilation.
  found: 85 backend tests passed before the final additive API error-detail test; the production `vinext build` completed successfully. The final focused suite covering the additive test also passed.
  implication: No observed regression in adjacent email, confirmation, Google, calendar, or robot behavior, and the frontend change type-checks/bundles.

- timestamp: 2026-08-30T11:04:01.4441487+05:30
  checked: Running localhost backend process.
  found: Uvicorn is running without `--reload`, so it continues serving the old transcription code until restarted. An attempted exact-process restart was blocked by the execution policy before any process was changed.
  implication: A backend restart is required before browser verification; frontend code is already compatible with hot reload.

- timestamp: 2026-08-30T11:27:00+05:30
  checked: Current backend transcription boundary, API validation, frontend recorder, timeout, configuration, dependencies, and focused tests.
  found: `/api/voice/transcribe` synchronously calls `GeminiReasoningService` directly; there is no STT provider interface. Browser recordings are at most 15 seconds and the request timeout is 45 seconds. Whisper is not declared in requirements or configuration.
  implication: A small provider orchestrator can be introduced without altering the browser contract; it must lazy-load the CPU model to avoid backend startup cost and retain the existing Gemini implementation as fallback.

- timestamp: 2026-08-30T11:27:00+05:30
  checked: User-selected dedicated STT options against local credentials and packages.
  found: No OpenAI or ElevenLabs API key is available; `openai-whisper` 20250625 and torch 2.10.0 are installed, CUDA is unavailable, and the Whisper base checkpoint is already cached locally.
  implication: Local Whisper is the only dedicated STT provider immediately usable without requiring a new account, credential, or network quota.

- timestamp: 2026-08-30T11:30:00+05:30
  checked: Local runtime prerequisites for the cached Whisper checkpoint.
  found: The 138.5 MB `base.pt` checkpoint exists, torch is CPU-only, and ffmpeg 8.1 is callable from `C:\\ffmpeg\\ffmpeg\\bin\\ffmpeg.exe`.
  implication: Local inference can decode every MIME type already accepted by the API; no provider signup or model download is required on this machine.

- timestamp: 2026-08-30T11:33:00+05:30
  checked: First synthetic benchmark harness attempt.
  found: The command runner rejected a compound script that created, benchmarked, and deleted a temporary audio file; no command executed and application state was unchanged.
  implication: Run temporary audio creation and inference as separate, non-destructive commands.

- timestamp: 2026-08-30T11:38:00+05:30
  checked: Cached Whisper base cold-start benchmark on a 4.3-second synthesized email command.
  found: Model load took 1.81 seconds and CPU transcription took 5.42 seconds (7.23 seconds total), returning `Send an email to Alice at example.com saying I love you, bububu.`
  implication: Local base is comfortably inside the 45-second browser timeout and preserves the consequential imperative. It should be the primary recorded-command provider; the address form needs deterministic normalization coverage and uncommon names/message words still benefit from confirmation.

- timestamp: 2026-08-30T11:45:00+05:30
  checked: First combined implementation patch.
  found: Patch validation stopped at a README text-encoding mismatch before applying any file changes.
  implication: Apply the provider, wiring, tests, and documentation as smaller independently verifiable patches.

- timestamp: 2026-08-30T11:56:00+05:30
  checked: Focused provider, API, Gemini fallback, and intent regression suites after implementation.
  found: 63 tests passed, covering lazy single load, local-first order, cloud fallback, matching MIME suffixes, temp-file cleanup, API validation/error mapping, and existing email entity extraction.
  implication: The dedicated provider is integrated without breaking the current voice API or adjacent intent behavior.

- timestamp: 2026-08-30T12:00:00+05:30
  checked: Real cached-model round trip through `LocalWhisperTranscriptionService`, provider orchestration, and deterministic email parsing.
  found: The service selected `local-whisper`, transcribed the representative command, classified it as `SEND_EMAIL`, recovered `alice@example.com`, preserved the message body, and reported no provider error.
  implication: The implemented boundary works with the actual cached model and ffmpeg, not only test doubles; recipient normalization downstream handles Whisper's `Alice at example.com` rendering.

- timestamp: 2026-08-30T12:04:00+05:30
  checked: Complete backend regression suite after local Whisper integration.
  found: All 91 tests passed. The only output was two pre-existing dependency deprecation/future warnings.
  implication: No observed regression in email, confirmation, calendar, robot, API, Gemini, or voice behavior.

- timestamp: 2026-08-30T12:20:00+05:30
  checked: Human verification of the local Whisper performance checkpoint.
  found: The user reports that recent local transcription takes too long and prefers an API-key-backed provider.
  implication: The functional local-first fix fails the real workflow's latency requirement; local Whisper should become the final fallback rather than the normal path when hosted STT is configured.

- timestamp: 2026-08-30T12:22:00+05:30
  checked: Complete transcription provider, configuration, voice API boundary, tests, dependency list, ignore rules, and local setup documentation.
  found: `VoiceTranscriptionService` invokes local Whisper before even checking the hosted Gemini provider. The API accepts an audio blob and delegates through one synchronous provider-neutral method; `requests` is already installed and `secrets/` is gitignored.
  implication: Provider ordering, not the browser contract, is the confirmed latency cause. A small requests-based OpenAI provider can be primary, with Gemini second and CPU Whisper last.

- timestamp: 2026-08-30T12:25:00+05:30
  checked: New hosted-provider and provider-order regression tests against the unchanged implementation.
  found: Test collection fails because `OpenAITranscriptionService` does not exist; the tests also encode that OpenAI must short-circuit Gemini and local Whisper, while local must execute only after hosted failures.
  implication: The regression suite reproduces the missing capability before the production fix and will distinguish the intended latency fix from a superficial configuration change.

- timestamp: 2026-08-30T12:31:00+05:30
  checked: Focused OpenAI provider and provider-order suite after implementation.
  found: All 9 tests pass, including multipart audio construction, command-context prompting, environment/file key precedence, sanitized 429 handling, hosted short-circuiting, and local-last fallback.
  implication: The minimal provider boundary satisfies the intended latency path in isolation without removing either existing fallback.

- timestamp: 2026-08-30T12:35:00+05:30
  checked: Combined transcription-provider and `/api/voice/transcribe` boundary suites plus setup documentation.
  found: All 20 focused tests pass. Documentation now names `OPENAI_API_KEY` and gitignored `secrets/openai_api_key.txt`, the required backend restart, provider order, and opt-out settings.
  implication: The existing browser upload contract and safe user-facing API error mapping remain compatible with the hosted-first change.

- timestamp: 2026-08-30T12:38:00+05:30
  checked: Complete backend regression suite.
  found: All 95 tests pass; only two pre-existing dependency deprecation/future warnings remain.
  implication: No observed regression in adjacent email, confirmation, calendar, robot, API, Gemini, or voice behavior.

- timestamp: 2026-08-30T12:40:00+05:30
  checked: OpenAI key-source presence and a direct uvicorn process-name filter.
  found: Neither `OPENAI_API_KEY` nor `secrets/openai_api_key.txt` is configured. No process command line matched the direct uvicorn filter.
  implication: A real hosted transcription request cannot be performed without the user's credential; port ownership must be checked separately to determine restart instructions.

- timestamp: 2026-08-30T12:41:00+05:30
  checked: TCP listener ownership for localhost port 8000.
  found: Python process 7724 is serving `backend.api:app` through uvicorn.
  implication: The backend is running; only its reload flag remains to determine whether code changes are already loaded. A restart is still required after adding a new key because configuration is read at process startup/global service construction boundaries.

- timestamp: 2026-08-30T12:43:00+05:30
  checked: Reload mode of the active backend process.
  found: Port 8000 process 7724 runs uvicorn with `--reload`, so Python source changes are automatically picked up.
  implication: The implementation is live, but a one-time backend restart after credential setup remains the clearest verification baseline, especially when using an environment variable.

## Resolution

root_cause: Inline wake commands originally bypassed server STT, while recorded commands depended on quota-limited Gemini. The first dedicated-STT fix made CPU-only local Whisper the unconditional primary; its measured approximately 7.23-second cold command path was accurate but too slow in the user's real workflow.
fix: Browser wake alternative ranking and all prior safety behavior remain. Recorded uploads now use OpenAI `gpt-4o-mini-transcribe` first when configured, Gemini second, and cached local Whisper last. OpenAI accepts `OPENAI_API_KEY` or gitignored `secrets/openai_api_key.txt`, receives deterministic command/email context, and maps errors without exposing keys or provider response bodies.
verification: All 20 focused provider/API tests and all 95 backend tests pass. Tests cover multipart request construction, key precedence, sanitized failures, hosted short-circuiting, and local-last failover. The active backend uses auto-reload. Real hosted latency verification remains blocked only by the intentionally absent OpenAI credential.
files_changed:
  - backend/services/gemini_reasoning_service.py
  - backend/services/transcription_service.py
  - backend/config.py
  - backend/api.py
  - backend/tests/test_gemini_reasoning_service.py
  - backend/tests/test_transcription_service.py
  - backend/tests/test_api.py
  - requirements.txt
  - README.md
  - frontend/app/lib/wake-phrase.ts
  - frontend/app/page.tsx
  - frontend/tests/wake-phrase.test.mjs
