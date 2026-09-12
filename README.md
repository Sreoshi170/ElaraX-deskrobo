<div align="center">

# 🤖 ElaraX

### A multilingual, safety-first executive assistant with real Gmail, Calendar & robot control

ElaraX pairs a **Gemini planning layer** with a **LangGraph Supervisor backend** to plan, speak, and act across email, calendar, research, and robotics — while every consequential action waits behind a deterministic confirmation gate before it runs.

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev/)
[![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![Gemini](https://img.shields.io/badge/Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![Groq](https://img.shields.io/badge/Groq-F55036?style=for-the-badge&logo=lightning&logoColor=white)](https://groq.com/)
[![Google APIs](https://img.shields.io/badge/Google_APIs-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://developers.google.com/workspace)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/langgraph)
[![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org/)
[![PowerShell](https://img.shields.io/badge/PowerShell-5391FE?style=for-the-badge&logo=powershell&logoColor=white)](https://learn.microsoft.com/powershell/)

[![GitHub stars](https://img.shields.io/github/stars/Sreoshi170/ElaraX-deskrobo?style=for-the-badge&logo=github&label=Stars)](https://github.com/Sreoshi170/ElaraX-deskrobo/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Sreoshi170/ElaraX-deskrobo?style=for-the-badge&logo=github&label=Forks)](https://github.com/Sreoshi170/ElaraX-deskrobo/forks)
[![GitHub last commit](https://img.shields.io/github/last-commit/Sreoshi170/ElaraX-deskrobo?style=for-the-badge&logo=github&label=Last%20Commit)](https://github.com/Sreoshi170/ElaraX-deskrobo/commits/main)
[![Repo size](https://img.shields.io/github/repo-size/Sreoshi170/ElaraX-deskrobo?style=for-the-badge&logo=github&label=Repo%20Size)](https://github.com/Sreoshi170/ElaraX-deskrobo)

</div>

---

## 📚 Table of Contents

- [✨ Key Features](#-key-features)
- [🛠️ Technology Stack](#️-technology-stack)
- [🧭 Application Flow](#-application-flow)
- [🖥️ Application Areas](#️-application-areas)
- [🚀 Run Locally](#-run-locally)
- [📁 Detailed File Structure](#-detailed-file-structure)
- [🔐 Safety Summary](#-safety-summary)
- [🧪 Verify](#-verify)

---

## ✨ Key Features

### 🧠 Assistant core

- Gemini-powered planning layer with deterministic intent routing as a safety fallback
- LangGraph **Supervisor** architecture routing to `assistant`, `email`, `calendar`, `briefing`, `robot`, and `market_research` specialists
- 🚦 Deterministic confirmation gates on every consequential email, calendar, or robot action — nothing fires without explicit approval
- 🔍 Source-grounded market research with a **Wili → Tavily → DuckDuckGo** provider chain and no invented citations

### 🎙️ Voice and language

- "Hey Elara" wake-word activation plus manual microphone control
- 🌐 Native support for **English, Bengali, Hindi**, and code-mixed speech
- Three-tier STT fallback: **Groq `whisper-large-v3` → Gemini audio → cached local Whisper `base`**
- Three-tier TTS fallback: **Gemini 3.1 Flash TTS (Kore voice) → `edge-tts` neural voices → browser speech synthesis**
- 🔁 Spoken approval/cancellation for pending confirmations

### 📬 Email and productivity

- Full Gmail control: read, search, summarize, draft, send, forward, star, archive, and delete
- 🧾 Automated invoice acknowledgement replies with safe, non-committal fixed responses
- 📆 Real Google Calendar access through the same confirmation-gated flow
- 🔗 Context-aware follow-ups — *"send the draft"* reuses the active recipient, subject, and body

### 💻 Frontend experience

- Responsive local command-center UI built for desktop and mobile
- Live status, transcription, and confirmation prompts in one composer
- 🌗 Consistent UI across voice, chat, and confirmation interactions

<div align="center">
<sub>Preview images: <code>elarax-desktop.png</code> · <code>elarax-mobile.png</code></sub>
</div>

---

## 🛠️ Technology Stack

### 🔒 Backend & AI

<div align="center">

| Layer | Technology |
|:---|:---|
| 🐍 **Backend** | ![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![Uvicorn](https://img.shields.io/badge/-Uvicorn-2A9D8F?style=flat-square&logo=gunicorn&logoColor=white) |
| 🕸️ **Orchestration** | ![LangGraph](https://img.shields.io/badge/-LangGraph_Supervisor-1C3C3C?style=flat-square&logo=langchain&logoColor=white) |
| 🧠 **Reasoning** | ![Gemini](https://img.shields.io/badge/-Gemini_3.5_Flash_Lite-8E75B2?style=flat-square&logo=googlegemini&logoColor=white) |
| 🎙️ **Speech-to-text** | ![Groq](https://img.shields.io/badge/-Groq_Whisper--v3-F55036?style=flat-square&logo=lightning&logoColor=white) ![Whisper](https://img.shields.io/badge/-Local_Whisper-412991?style=flat-square&logo=openai&logoColor=white) |
| 🔊 **Text-to-speech** | ![Gemini TTS](https://img.shields.io/badge/-Gemini_TTS-8E75B2?style=flat-square&logo=googlegemini&logoColor=white) ![edge-tts](https://img.shields.io/badge/-edge--tts-0078D4?style=flat-square&logo=microsoft&logoColor=white) ![gTTS](https://img.shields.io/badge/-gTTS-4285F4?style=flat-square&logo=google&logoColor=white) |
| 🔗 **Integrations** | ![Gmail](https://img.shields.io/badge/-Gmail_API-EA4335?style=flat-square&logo=gmail&logoColor=white) ![Calendar](https://img.shields.io/badge/-Google_Calendar-4285F4?style=flat-square&logo=googlecalendar&logoColor=white) |
| 🌍 **Research** | ![Tavily](https://img.shields.io/badge/-Tavily-000000?style=flat-square) ![DuckDuckGo](https://img.shields.io/badge/-DuckDuckGo-DE5833?style=flat-square&logo=duckduckgo&logoColor=white) ![OpenRouter](https://img.shields.io/badge/-OpenRouter-000000?style=flat-square) |
| 🧪 **Testing** | ![Pytest](https://img.shields.io/badge/-Pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white) |

</div>

### 🎨 Frontend

<div align="center">

| Layer | Technology |
|:---|:---|
| ⚛️ **Frontend** | ![React](https://img.shields.io/badge/-React-20232A?style=flat-square&logo=react&logoColor=61DAFB) ![Node.js](https://img.shields.io/badge/-Node.js-339933?style=flat-square&logo=nodedotjs&logoColor=white) ![npm](https://img.shields.io/badge/-npm-CB3837?style=flat-square&logo=npm&logoColor=white) |
| 🎙️ **Voice UI** | ![WebAudio](https://img.shields.io/badge/-Web_Audio_API-FF6B6B?style=flat-square) ![WebSpeech](https://img.shields.io/badge/-Web_Speech_API-4A90D9?style=flat-square) |
| 🎨 **Design** | ![CSS3](https://img.shields.io/badge/-CSS3-1572B6?style=flat-square&logo=css3&logoColor=white) Responsive command-center layout |

</div>

### 🧰 Full Stack at a Glance

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Gemini](https://img.shields.io/badge/Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-F55036?style=for-the-badge&logo=lightning&logoColor=white)
![Gmail](https://img.shields.io/badge/Gmail_API-EA4335?style=for-the-badge&logo=gmail&logoColor=white)
![Google Calendar](https://img.shields.io/badge/Google_Calendar-4285F4?style=for-the-badge&logo=googlecalendar&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)

</div>

---

## 🧭 Application Flow

```
flowchart LR
    U[🎙️ User voice / text] --> F[💻 React command center]
    F --> API[⚡ FastAPI backend]
    API --> S[🕸️ LangGraph Supervisor]
    S --> E[📬 Email agent]
    S --> C[📆 Calendar agent]
    S --> B[📋 Briefing agent]
    S --> R[🤖 Robot agent]
    S --> M[🔍 Market research agent]
    E --> G[🚦 Gate: POST /api/confirm]
    C --> G
    R --> G
    G --> X[✅ Executed action]
```

1. 🎙️ The user speaks or types a command through the command-center UI.
2. 🔤 Audio is transcribed through the **Groq → Gemini → local Whisper** fallback chain, with language auto-detection across English, Hindi, Bengali, and code-mixed speech.
3. 🕸️ The request enters the **LangGraph Supervisor**, which routes it to the right specialist.
4. 📖 Specialists that read data (briefing, research, inbox summaries) respond immediately.
5. 🚦 Specialists that would change something — sending an email, editing a calendar event, moving the robot — stop at a **confirmation step** first.
6. ✅ The user approves or cancels by voice or by tapping the prompt.
7. 🔊 Approved actions execute through Gmail, Calendar, or the robot interface, and the response is spoken back using the TTS fallback chain.

---

## 🖥️ Application Areas

| Area | Purpose | Experience |
|:---|:---|:---|
| 🎛️ **Command composer** | Send text or voice commands | Language mode selector, wake-word toggle, microphone and replay controls |
| 📬 **Email assistant** | Manage Gmail end-to-end | Inbox summaries, drafting, confirmation-gated sending, invoice auto-replies |
| 📆 **Calendar assistant** | View and manage events | Natural-language scheduling with confirmation before changes |
| 📋 **Briefing agent** | Daily summary of email, calendar, and priorities | Condensed, spoken-friendly overview |
| 🔍 **Market research** | Source-grounded research answers | Wili/Tavily/DuckDuckGo retrieval with explicit warnings instead of fabricated sources |
| 🤖 **Robot control** | Send and monitor robot commands | Status polling and confirmation-gated command dispatch |

---

## 🚀 Run Locally

### ✅ Prerequisites

- 🐍 Python 3.10+
- 🟢 Node.js and npm
- 🔑 A free [Groq API key](https://console.groq.com/keys)
- 🔑 A Gemini API key
- 🔐 A Google Cloud OAuth client for Gmail/Calendar (for full functionality)

### 📋 Steps

**1. Clone the repository**

```bash
git clone https://github.com/Sreoshi170/ElaraX-deskrobo.git
cd ElaraX-deskrobo
```

**2. Install Python dependencies**

```bash
python -m pip install -r requirements.txt
```

**3. Configure environment variables**

Copy `.env.example` to `.env` and add your keys:

```env
GROQ_API_KEY=gsk_your_key_here
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3
GEMINI_API_KEY=your_gemini_key_here
```

**4. Launch — one command**

```powershell
.\start.ps1
```

**Or run backend + frontend separately:**

```bash
# Terminal 1 — backend
python -m uvicorn backend.api:app --reload --port 8000
```

```bash
# Terminal 2 — frontend
cd frontend
npm run dev
```

**5. Open the app**

```
http://localhost:3000
```

📖 API documentation is available at `http://localhost:8000/docs`.

> ⚠️ Never commit `.env`, share it in screenshots, or paste its contents into logs. `.env.example` documents every setting without real credentials.

---

## 📁 Detailed File Structure

```
ElaraX-deskrobo/
│
├── 📂 backend/                        # FastAPI + LangGraph application
│   ├── api.py                         # FastAPI entry point — /api/chat, /api/confirm, /api/research, etc.
│   ├── supervisor/                    # LangGraph Supervisor graph & routing logic
│   │   └── graph.py                   # Registers assistant / email / calendar / briefing / robot / market_research
│   ├── agents/                        # Individual specialist agents
│   │   ├── assistant_agent.py
│   │   ├── email_agent.py             # Gmail read/search/draft/send/archive/delete
│   │   ├── calendar_agent.py          # Google Calendar CRUD
│   │   ├── briefing_agent.py          # Daily summary generation
│   │   ├── robot_agent.py             # Robot status + command dispatch
│   │   └── market_research_agent.py   # Wili → Tavily → DuckDuckGo retrieval
│   ├── voice/                         # Speech pipeline
│   │   ├── stt.py                     # Groq → Gemini → local Whisper fallback chain
│   │   └── tts.py                     # Gemini TTS → edge-tts → gTTS fallback chain
│   ├── integrations/                  # External API clients
│   │   ├── gmail_client.py
│   │   ├── calendar_client.py
│   │   └── oauth.py                   # Google OAuth token handling
│   ├── safety/
│   │   └── confirmation_gate.py       # Deterministic confirm/cancel logic for consequential actions
│   └── config.py                      # Loads .env and exposes settings
│
├── 📂 frontend/                       # React command-center UI
│   ├── src/
│   │   ├── components/                # Composer, confirmation prompts, chat bubbles, mic controls
│   │   ├── pages/                     # Main dashboard / command-center views
│   │   ├── hooks/                     # Voice capture, language mode, wake-word hooks
│   │   └── App.jsx
│   ├── public/
│   └── package.json
│
├── 📂 context/                        # Supporting prompt / context assets used by agents
│
├── 📂 .planning/                      # Project planning notes and design docs
│
├── 🖼️ aetherbot-og.png                # Open-graph preview image
├── 🖼️ elarax-desktop.png              # Desktop UI screenshot
├── 🖼️ elarax-mobile.png               # Mobile UI screenshot
├── 📦 aetherbot-site.tar.gz           # Packaged static site build
│
├── 📄 agents.txt / agents.md.txt      # Agent behavior / prompt notes
├── 📄 check_stt.txt                   # STT pipeline verification notes
├── 🐍 refactor_vad.py                 # Voice-activity-detection refactor script
├── 🐍 refactor_vad_2.py               # VAD refactor script (iteration 2)
│
├── 🧪 pytest.ini                      # Pytest configuration
├── 🧪 pytest_out.txt                  # Saved test run output
├── 🧪 pytest_out_2.txt                # Saved test run output (2nd run)
│
├── 🔐 .env.example                    # Documented environment variables (no real secrets)
├── 🚫 .gitignore                      # Ignores .env, tokens, OAuth JSON, build artifacts
├── 📋 requirements.txt                # Python dependencies
├── ⚙️ start.ps1                        # One-command local launcher (Windows PowerShell)
└── 📖 README.md
```

> 💡 The `backend/` and `frontend/` internals above reflect the modules described by the project's own documentation (Supervisor specialists, STT/TTS fallback chains, confirmation gate). Exact file names may differ slightly — check the folders directly on GitHub for the current layout.

---

## 🔐 Safety Summary

| Protection | Purpose |
|:---|:---|
| 🚦 **Confirmation gate** (`POST /api/confirm`) | Blocks any email, calendar, or robot mutation until the user explicitly approves it |
| 🧭 **Deterministic routing fallback** | Keeps safety policy enforced even if Gemini is unavailable |
| 🧾 **Invoice auto-reply guardrails** | Never states an invoice is approved or paid; skips no-reply and reminder threads |
| 🔍 **Source-grounded research** | Returns an explicit warning instead of inventing citations when retrieval fails |
| 🔐 **Local secret handling** | `.env`, OAuth JSON, and Google tokens stay git-ignored and local-only |

---

## 🧪 Verify

```bash
python -m pytest -q
```

```bash
cd frontend
npm run build
```

---

<div align="center">

### 🌟 Built for fast, multilingual, and safety-gated executive assistance 🌟

</div>
