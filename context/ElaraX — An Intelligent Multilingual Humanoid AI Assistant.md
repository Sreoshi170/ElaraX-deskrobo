
# ElaraX — An Intelligent Multilingual Humanoid AI Assistant

**Team:** The Missing Semicolon  
**Project Type:** Hybrid Software + Hardware  
**Project Category:** Multilingual AI, Agentic AI, Productivity Automation, RAG, Robotics  
**Primary Hardware:** ESP32 Mini 3

## 1. Project Overview

ElaraX is a **multilingual, embodied AI executive assistant** that combines a software-based intelligent workspace assistant with a small physical desk robot.

The software understands natural voice and text commands, manages emails and meetings, summarizes information, performs market research, and provides contextual assistance. The hardware gives the assistant a physical presence through desk movement, voice interaction, visual notifications, and a display.

The central idea is to create a **unified AI workspace companion** that can understand what the user needs, decide which specialized agent should handle the task, execute approved actions, and communicate the result through both software and hardware.

ElaraX supports **English, Bengali, Hindi, and code-mixed conversations**.

---

## 2. Problem Statement

Modern digital work is fragmented across multiple applications:

- Emails are scattered across inboxes and threads.
- Important messages can be missed among routine notifications.
- Meeting schedules require repeated manual checking.
- Replying to emails is repetitive and time-consuming.
- Market research requires collecting information from multiple sources.
- Users must switch between Gmail, Calendar, research tools, and other applications.
- Existing assistants are often limited to software interfaces and do not provide a physical, interactive presence.

There is a gap for a **unified software–hardware assistant** that can understand multilingual commands, manage digital tasks, perform research, and communicate through a physical robot.

---

## 3. Proposed Solution

ElaraX acts as a **personal AI executive assistant and desk companion**.

The user can say:

> “আমার important emails গুলো বলো।”

> “आज मेरी meetings क्या हैं?”

> “Summarize my unread emails.”

> “Reply to this email saying I will attend.”

> “Schedule a Google Meet with Rahul tomorrow at 4 PM.”

> “Research the electric vehicle market and give me a SWOT analysis.”

ElaraX processes the request, identifies the appropriate task, routes it to a specialized agent, retrieves information when necessary, performs the required operation, and returns a response in the user's preferred language.

For consequential actions such as sending an email or creating a meeting, the system asks for **user confirmation before execution**.

---

## 4. Main Objectives

1. Build a multilingual AI assistant using **LangGraph-based agents**.
2. Create a physical desk robot controlled by **ESP32 Mini 3**.
3. Integrate email reading, summarization, prioritization, and reply drafting.
4. Support Google Calendar and Google Meet scheduling.
5. Add a market research agent using **RAG and SWOT analysis**.
6. Use **Groq API** for fast LLM inference where appropriate.
7. Use **Gemini API** for reasoning and general assistant capabilities.
8. Use **FastAPI** as the backend.
9. Provide voice-to-text and text-to-speech interaction.
10. Maintain conversational context and user preferences.
11. Ensure safe, human-approved automation.
12. Demonstrate a working software–hardware prototype for the hackathon.

---

## 5. Core Features

### 5.1 Multilingual Voice Interaction

ElaraX accepts voice commands in:

- English
- Bengali
- Hindi
- Bengali-English code-mixing
- Hindi-English code-mixing

**Flow:**

```text
User Voice
    ↓
ElevenLabs Speech-to-Text
    ↓
Language Detection
    ↓
Intent Classification
    ↓
Specialized Agent
    ↓
Response Generation
    ↓
ElevenLabs Text-to-Speech
    ↓
Speaker / Robot
```

The user can speak naturally without needing to use exact commands.

### 5.2 Email Intelligence

ElaraX can:

- Read emails.
- Fetch unread emails.
- Summarize individual emails.
- Summarize entire threads.
- Identify urgent or important emails.
- Prioritize emails based on context.
- Find emails using natural language.
- Draft replies.
- Send replies after confirmation.
- Provide spoken email briefings.

**Example:**

> “Which emails need my attention today?”

The system retrieves relevant emails, analyzes their content and context, ranks them, and presents the most important items first.

### 5.3 Meeting and Calendar Management

ElaraX can:

- Check today's schedule.
- Check tomorrow's schedule.
- Find available time slots.
- Create Google Meet meetings.
- Reschedule meetings.
- Cancel meetings.
- Detect scheduling conflicts.
- Read meeting details aloud.
- Provide reminders through the robot.

**Example:**

> “Schedule a meeting with Rahul tomorrow at 4 PM.”

The system extracts the participant, date, and time, checks availability, prepares the meeting, asks for confirmation, and then creates the event.

### 5.4 Daily Briefing

The briefing agent combines information from multiple sources:

```text
Important Emails
       +
Today's Calendar
       +
Pending Actions
       +
Market Research Updates
       ↓
Daily Briefing Agent
       ↓
Personalized Morning Briefing
```

Example:

> “Good morning. You have three important emails, two meetings today, and one pending reply.”

### 5.5 Market Research and SWOT Analysis

The new **Market Research Agent** is a specialized research assistant.

It can:

- Research a company, product, industry, or market.
- Collect information from approved sources.
- Retrieve relevant documents using RAG.
- Summarize research findings.
- Identify market trends.
- Compare competitors.
- Extract opportunities and risks.
- Generate a **SWOT analysis**.
- Provide source-grounded answers.
- Present findings in a structured report.

**Example:**

> “Research the electric vehicle market and give me a SWOT analysis.”

The agent retrieves relevant information, analyzes the evidence, and produces:

- Market overview
- Key trends
- Major competitors
- Strengths
- Weaknesses
- Opportunities
- Threats
- Sources and supporting evidence

### 5.6 Physical Desk Robot

The hardware companion can:

- Move forward and backward.
- Turn left and right.
- Stop immediately.
- Display messages.
- Show email and meeting notifications.
- Indicate listening, processing, success, and warning states.
- Play voice responses.
- React to important events.
- Display the current task or briefing.
- Provide a physical presence for the AI assistant.

The robot is not intended to perform complex autonomous navigation. It is a **small, controlled desk companion** focused on interaction and productivity.

---

## 6. System Architecture

```text
                         ┌──────────────────────┐
                         │       User           │
                         │ Voice / Text Command │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   React Frontend     │
                         │   Dashboard + Chat   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     FastAPI Backend  │
                         │   API + WebSocket    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   LangGraph          │
                         │   Supervisor Agent   │
                         └──────────┬───────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
      ┌────────────┐       ┌────────────┐       ┌────────────┐
      │ Email Agent│       │Calendar    │       │Market      │
      │            │       │Agent       │       │Research    │
      └─────┬──────┘       └─────┬──────┘       │Agent       │
            │                    │              └─────┬──────┘
            ▼                    ▼                    ▼
      Gmail API          Calendar / Meet API     RAG + SWOT
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │
                                  ▼
                         ┌──────────────────────┐
                         │   Response / Voice   │
                         │   ElevenLabs TTS     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   ESP32 Mini 3       │
                         │   Desk Robot         │
                         └──────────────────────┘
```

---

## 7. LangGraph Agent Architecture

All primary agents are built using **LangGraph**.

The supervisor is responsible for coordinating the workflow. Specialized agents handle specific tasks.

```text
START
  ↓
Emergency Stop Guard
  ↓
Language Detection
  ↓
Intent Classification
  ↓
Supervisor Agent
  ↓
Route to Specialized Agent
  ├── Email Agent
  ├── Calendar Agent
  ├── Market Research Agent
  ├── Briefing Agent
  ├── Robot Agent
  └── General Assistant Agent
  ↓
Response Generation
  ↓
Human Confirmation (if required)
  ↓
Tool Execution
  ↓
Final Response
  ↓
END
```

### 7.1 Supervisor Agent

The supervisor is the **central coordinator** of ElaraX.

It does not directly perform every task. Instead, it:

- Understands the user's request.
- Identifies the required capability.
- Selects the appropriate specialized agent.
- Maintains workflow context.
- Coordinates multi-agent tasks.
- Handles incomplete or ambiguous requests.
- Collects results from agents.
- Decides whether another agent is needed.
- Routes the final response.

**Example:**

> “Read my important emails and tell me if I have any meetings related to them.”

The supervisor may route:

```text
Supervisor
    ↓
Email Agent → Important Emails
    ↓
Calendar Agent → Related Meetings
    ↓
Supervisor → Combined Response
```

### 7.2 Email Agent

The Email Agent handles Gmail-related tasks.

**Responsibilities:**

- Fetch emails.
- Search emails.
- Read email content.
- Summarize emails.
- Prioritize emails.
- Draft replies.
- Prepare sending actions.
- Execute sending only after approval.

### 7.3 Calendar Agent

The Calendar Agent handles scheduling.

**Responsibilities:**

- Read calendar events.
- Check availability.
- Detect conflicts.
- Create meetings.
- Reschedule meetings.
- Cancel meetings.
- Generate Google Meet links.
- Request confirmation before consequential actions.

### 7.4 Market Research Agent

The Market Research Agent is the new research-focused agent.

**Responsibilities:**

- Understand the research question.
- Identify the topic and scope.
- Retrieve relevant information.
- Use RAG to ground responses.
- Analyze market trends.
- Compare competitors.
- Generate SWOT analysis.
- Summarize findings.
- Return source-grounded results.

### 7.5 Briefing Agent

The Briefing Agent combines information from multiple agents.

**Responsibilities:**

- Collect important emails.
- Collect calendar events.
- Collect pending actions.
- Include relevant research updates.
- Rank information by importance.
- Generate a personalized briefing.

### 7.6 Robot Agent

The Robot Agent translates high-level requests into safe robot commands.

**Responsibilities:**

- Validate robot commands.
- Control movement.
- Control LEDs.
- Control display.
- Control buzzer.
- Read sensor status.
- Report robot state.

The Robot Agent must never allow the LLM to directly generate unrestricted motor-control instructions.

---

## 8. Market Research Agent — Detailed Architecture

```text
User Research Query
        ↓
Research Intent Extraction
        ↓
Supervisor Routes to Market Research Agent
        ↓
Query Understanding
        ↓
Source Selection
        ↓
Document Retrieval
        ↓
RAG Context Construction
        ↓
Groq / LLM Analysis
        ↓
SWOT Analysis
        ↓
Structured Research Report
        ↓
Response to User
```

### 8.1 RAG Pipeline

```text
Research Documents
       ↓
Document Loading
       ↓
Text Extraction
       ↓
Text Chunking
       ↓
Embedding Generation
       ↓
Vector Database
       ↓
User Query
       ↓
Similarity Search
       ↓
Relevant Context
       ↓
LLM
       ↓
Grounded Answer
```

### 8.2 SWOT Analysis

The Market Research Agent generates:

| Category | Meaning |
|---|---|
| **Strengths** | Internal advantages |
| **Weaknesses** | Internal limitations |
| **Opportunities** | External growth possibilities |
| **Threats** | External risks |

The analysis should be based on retrieved evidence rather than unsupported assumptions.

### 8.3 Groq API

Groq will be used for **fast LLM inference**, especially where low-latency responses are useful.

Possible uses:

- Intent classification.
- Research analysis.
- SWOT generation.
- Summarization.
- Fast conversational responses.

The exact Groq model will be selected during implementation based on availability, performance, and free-tier constraints.

### 8.4 Gemini API

Gemini will be used where its capabilities are suitable for:

- General assistant reasoning.
- Structured response generation.
- Context-aware assistance.
- Multilingual understanding.
- Complex task interpretation.

The architecture should keep the LLM provider configurable so that Gemini and Groq can be used without rewriting the entire system.

---

## 9. Software Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, HTML, CSS |
| Backend | Python, FastAPI |
| Agent Framework | LangGraph |
| LLMs | Gemini API, Groq API |
| Speech-to-Text | ElevenLabs |
| Text-to-Speech | ElevenLabs |
| Email Integration | Gmail API |
| Calendar Integration | Google Calendar API |
| Meeting Integration | Google Meet API |
| RAG | Document loaders, embeddings, vector database |
| Database | SQLite |
| Authentication | OAuth 2.0 |
| Hardware Controller | ESP32 Mini 3 |
| Communication | Wi-Fi / Bluetooth |
| Testing | Pytest |
| Version Control | Git / GitHub |

---

## 10. Hardware Architecture

### Hardware Components

- ESP32 Mini 3
- Microphone
- Speaker
- MAX98357 amplifier
- INMP441 microphone module
- OLED / TFT display
- DC motors
- Motor driver
- RGB LEDs
- Ultrasonic / IR / touch sensors
- Wi-Fi / Bluetooth
- Rechargeable battery
- Custom robot chassis

### Hardware Flow

```text
FastAPI Backend
      ↓
Robot Command
      ↓
ESP32 Mini 3
      ↓
Command Validation
      ↓
Motor / Display / LED / Speaker
      ↓
Robot Action
      ↓
Status Feedback
      ↓
Backend
```

### Example

```text
User: "Stop moving"

Voice → STT → STOP Intent
             ↓
      Emergency Stop Guard
             ↓
      Robot Stop Command
             ↓
        ESP32 Mini 3
             ↓
        Motors Stop
```

---

## 11. Human-in-the-Loop Safety

ElaraX must distinguish between **reading information** and **performing actions**.

### Read-Only Actions

These can execute without confirmation:

- Read email.
- Summarize email.
- Check calendar.
- Search documents.
- Generate research report.
- Generate SWOT analysis.
- Display information.

### Consequential Actions

These require confirmation:

- Send email.
- Create meeting.
- Reschedule meeting.
- Cancel meeting.
- Perform other external actions.

### Safety-Critical Actions

These must be handled immediately:

- Stop robot.
- Emergency stop.
- Disable movement.

**Example:**

```text
User: "Send this reply."

Draft Reply
    ↓
Confirmation Required
    ↓
User: "Yes"
    ↓
Send Email
    ↓
Success Response
```

---

## 12. Memory and Context

ElaraX maintains conversational context so that users can interact naturally.

Example:

> User: “Read my latest email.”  
> ElaraX: “Your latest email is from Rahul.”  
> User: “Reply saying I will attend.”

The system should understand that “reply” refers to the previously selected email.

Memory may include:

- Conversation history.
- User preferences.
- Preferred language.
- Selected email.
- Selected meeting.
- Pending actions.
- Research context.
- Robot state.

Sensitive data should be handled securely and stored only when necessary.

---

## 13. Example End-to-End Workflows

### Workflow A — Important Email Briefing

```text
User Voice
    ↓
ElevenLabs STT
    ↓
Language Detection
    ↓
Supervisor
    ↓
Email Agent
    ↓
Gmail API
    ↓
Fetch Emails
    ↓
Priority Analysis
    ↓
Summarization
    ↓
ElevenLabs TTS
    ↓
Robot Speaker
    ↓
Display Important Emails
```

### Workflow B — Schedule Google Meet

```text
User Voice
    ↓
Supervisor
    ↓
Calendar Agent
    ↓
Extract Participant + Date + Time
    ↓
Check Availability
    ↓
Prepare Meeting
    ↓
User Confirmation
    ↓
Google Calendar API
    ↓
Google Meet Created
    ↓
Robot Displays Meeting
    ↓
Voice Confirmation
```

### Workflow C — Market Research + SWOT

```text
User Query
    ↓
Supervisor
    ↓
Market Research Agent
    ↓
Query Understanding
    ↓
RAG Retrieval
    ↓
Relevant Documents
    ↓
Groq / LLM Analysis
    ↓
SWOT Generation
    ↓
Structured Research Report
    ↓
Display on Dashboard
    ↓
Read Summary Aloud
```

### Workflow D — Daily Briefing

```text
User: "Good morning"

Supervisor
    ↓
Briefing Agent
    ├── Email Agent
    ├── Calendar Agent
    └── Pending Actions
    ↓
Combined Briefing
    ↓
Robot Speaks Summary
    ↓
Display Briefing
```

---

## 14. Innovation and Uniqueness

ElaraX is different from a conventional chatbot because it combines:

1. **Software + Hardware Integration**  
   A real physical desk companion rather than only a screen-based assistant.

2. **Multilingual Voice Interaction**  
   Supports English, Bengali, Hindi, and code-mixed communication.

3. **LangGraph-Based Multi-Agent Architecture**  
   Specialized agents collaborate through a supervisor.

4. **Context-Aware Assistance**  
   Understands follow-up commands and maintains task context.

5. **Intelligent Priority Detection**  
   Identifies important emails and urgent information.

6. **RAG-Based Market Research**  
   Provides source-grounded research and SWOT analysis.

7. **Human-Approved Automation**  
   Prevents unintended email and meeting actions.

8. **Embodied Notifications**  
   Uses movement, LEDs, display, and voice to communicate.

9. **Unified Workspace Assistant**  
   Combines email, calendar, research, and robot interaction in one system.

10. **Safe AI Automation**  
    Separates reasoning from tool execution and hardware control.

---

## 15. Expected Hackathon Prototype

The prototype should demonstrate:

- A working React dashboard.
- Voice and text input.
- Multilingual commands.
- LangGraph supervisor.
- Email Agent with mock or real Gmail integration.
- Calendar Agent with mock or real Calendar integration.
- Market Research Agent using RAG.
- SWOT analysis generation.
- Groq / Gemini integration.
- ElevenLabs voice output.
- ESP32 Mini 3 desk robot movement.
- Robot display and LED notifications.
- Human confirmation for email sending and meeting creation.

---

## 16. Future Scope

- More specialized agents.
- Advanced market intelligence.
- Personalized productivity analytics.
- More hardware sensors.
- Autonomous desk navigation.
- Face recognition with privacy controls.
- Additional languages.
- Mobile application.
- Voice wake-word detection.
- Advanced document understanding.
- Multi-user support.
- Enterprise productivity integration.

---

## 17. One-Line Project Definition

**ElaraX is a multilingual, LangGraph-powered embodied AI executive assistant that unifies email, calendar, market research, and intelligent automation through a software dashboard and an ESP32 Mini 3 desk robot.**

