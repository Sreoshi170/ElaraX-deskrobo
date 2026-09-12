# ElaraX

A multilingual executive assistant with a Gemini planning layer, a safety-first
LangGraph backend, real Gmail and Google Calendar access, and a responsive local
command-center UI. Consequential email, calendar, and robot actions stay behind
deterministic confirmation gates.

## Environment and secrets

The backend automatically loads the root `.env` file before reading its
configuration. The file is already ignored by Git. Add your Groq key here:

```dotenv
GROQ_API_KEY=gsk_your_key_here
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3
```

Create a free Groq key at <https://console.groq.com/keys>. Restart the backend
after changing `.env`. Never commit `.env`, send it in screenshots, or paste its
contents into logs. `.env.example` documents every supported setting without
containing credentials.

Gemini reasoning and spoken responses read `GEMINI_API_KEY` from `.env`. For
backward compatibility, ElaraX can still read `secrets/gemini_api_key.txt` when
the environment value is blank. Gmail and Calendar continue to use the OAuth
client referenced by `AETHERBOT_GOOGLE_CLIENT_FILE`; the downloaded JSON and
encrypted Google tokens remain ignored local files.

The Gemini reasoning model defaults to `gemini-3.5-flash-lite`. If Gemini is
unavailable, the graph falls back to deterministic intent routing instead of
bypassing safety policy.

## Voice commands

Recorded commands use Groq `whisper-large-v3` first. The request includes an
ElaraX-specific prompt for imperative commands, names, alphanumeric identifiers,
email addresses, and English, Bengali, Hindi, and code-mixed speech. Gemini audio
understanding is the second provider and cached local Whisper `base` is the final
offline fallback. This provider order keeps commands responsive while retaining
a safe degraded mode during a Groq outage or free-tier rate limit.

Set `AETHERBOT_DISABLE_GROQ_STT=1` to test the fallbacks or
`AETHERBOT_DISABLE_LOCAL_WHISPER=1` to disable offline transcription. ElaraX will
not download a missing local model unless `AETHERBOT_WHISPER_ALLOW_DOWNLOAD=1`.

Turn on **Hey Elara** in the top bar, then say “Hey Elara” followed by a command.
You can also say the wake phrase by itself and speak after the listening prompt,
or use the microphone button manually. Spoken approval or cancellation works
when an action is waiting, while email, calendar, and robot safety gates remain
enforced.

Assistant responses are spoken automatically with Gemini 3.1 Flash TTS Preview
and the Kore voice. If Gemini is unavailable, the backend uses the free,
keyless `edge-tts` neural voices pinned to one Microsoft voice per language:
`en-IN-PrabhatNeural`, `bn-IN-BashkarNeural`, and `hi-IN-MadhurNeural`.
The browser's built-in speech engine is only the final offline fallback and
selects a stable installed voice when one is available. Use the speaker button
to mute spoken output or the replay button to hear the latest response again.

## Email commands

The Email Agent supports checking inbox mail, reading messages, searching by
sender or topic, reading unread mail, summarizing and prioritizing messages,
listing sent/draft/starred mail, drafting replies and new messages, sending,
forwarding, marking read or unread, starring, archiving, moving to trash, and
permanent deletion. Sending and mailbox changes always create a confirmation
step first. Follow-ups such as "send the draft" reuse the current draft's
recipient, subject, body, and selected email or meeting context.

## Invoice auto-replies

Use **Enable auto-replies** in the Invoice assistant card after connecting Gmail.
ElaraX then checks every five minutes and sends one fixed acknowledgement to
each new unread invoice thread. It records processed threads locally, skips
no-reply/newsletter addresses and overdue reminders, and never states that an
invoice is approved or will be paid. Use **Pause auto-replies** to stop future
acknowledgements; normal email replies still use the usual confirmation flow.

## Run locally

Install dependencies and start both services:

```powershell
python -m pip install -r requirements.txt
.\start.ps1
```

Alternatively, use two terminals from the repository root:

```powershell
python -m uvicorn backend.api:app --reload --port 8000
```

```powershell
cd frontend
npm run dev
```

Open `http://localhost:3000`. API documentation is available at
`http://localhost:8000/docs`.

## Supervisor agents and research

All requests enter the existing Supervisor graph. The registered specialists
are `assistant`, `email`, `calendar`, `briefing`, `robot`, and
`market_research`. Market research is source-grounded: it uses a configured
Wili-compatible endpoint first (when both `WILI_API_KEY` and `WILI_BASE_URL`
are present), then `TAVILY_API_KEY`, and finally a public DuckDuckGo lookup.
Retrieved excerpts are analyzed through the OpenRouter-compatible provider
configured by `OPENROUTER_API_KEY` and the two OpenRouter model variables. If
retrieval or analysis is unavailable, the API returns an explicit warning
instead of inventing citations.

Useful API contracts are `POST /api/chat`, `POST /api/assistant/run`,
`POST /api/research`, `GET /api/agents`, `GET /api/robot/status`, and
`POST /api/robot/command`. Consequential email/calendar/robot mutations still
wait for `POST /api/confirm`.

### Multilingual voice

The command composer exposes `Auto detect`, English, Hindi, Bengali, and
code-mixed modes. The selected mode is sent through `/api/chat` and
`/api/voice/transcribe`, where Groq/Gemini STT is attempted first and the
cached multilingual Whisper model is the local fallback. Responses are
localized at the final graph boundary, and `/api/voice/synthesize` uses
language-aware Gemini/Edge voices with gTTS as a keyless Hindi/Bengali
fallback. The browser's speech synthesis remains the final fallback if all
server speech providers are unavailable.

## Verify

```powershell
python -m pytest -q
cd frontend
npm run build
```
