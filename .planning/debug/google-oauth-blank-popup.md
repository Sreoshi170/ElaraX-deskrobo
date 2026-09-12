---
status: resolved
trigger: "Blank white accounts.google.com popup after clicking Connect Google in local AetherBot UI"
created: 2026-08-28T14:14:22.0256149+05:30
updated: 2026-08-28T14:22:00+05:30
---

## Current Focus

hypothesis: Confirmed — Google OAuth is being loaded inside the Codex in-app browser's embedded popup, which Google disallows as an embedded user-agent.
test: The main agent should replace the embedded popup route with a localhost backend action that opens the authorization URL in the operating system's default browser, then have the frontend poll connection status until the callback stores credentials.
expecting: Clicking Connect Google opens the normal Google consent UI in Chrome or Edge; after callback, status becomes connected=true even though the system-browser window has no JavaScript opener relationship with AetherBot.
next_action: Main agent implements the system-browser launch endpoint and frontend status polling, then repeats the original workflow.

## Symptoms

expected: Clicking Connect Google opens Google's account consent page and completes connection for the user's personal account.
actual: A popup labeled accounts.google.com opens within the Codex in-app browser but remains blank white.
errors: No visible error message in the popup.
reproduction: Open http://localhost:3000 in the Codex embedded browser and click Connect Google.
started: First real personal-account authorization attempt.

## Eliminated

## Evidence

- timestamp: 2026-08-28T14:15:30.6459956+05:30
  checked: Frontend connection handler and API client.
  found: The UI creates a JavaScript popup with window.open and then assigns the Google authorization URL directly to popup.location; there is no system-browser launch path or status polling fallback.
  implication: The Google consent page inherits the Codex in-app browser/webview popup context shown in the screenshot.

- timestamp: 2026-08-28T14:15:30.6459956+05:30
  checked: Backend OAuth manager and live Google status endpoint.
  found: The backend validates a Web application client, requires the exact localhost callback URI, generates an accounts.google.com authorization URL using google-auth-oauthlib, and reports configured=true, connected=false, error=null.
  implication: Missing or malformed local credential configuration is not causing the blank page before consent.

- timestamp: 2026-08-28T14:18:08.5685472+05:30
  checked: Fresh authorization request, with credential values redacted from the observation.
  found: The URL uses HTTPS, host accounts.google.com, path /o/oauth2/auth, contains the expected OAuth parameter names, and Google returns HTTP 200 with HTML content to a normal external HTTP client.
  implication: URL generation, DNS/network access, and the Google authorization endpoint are working; the page is blank only in the embedded browser environment.

- timestamp: 2026-08-28T14:18:08.5685472+05:30
  checked: Current Google OAuth policy and embedded-webview guidance.
  found: Google's policy says developers must not direct authorization requests to embedded user-agents, and its migration guidance says to use the operating system's default browser instead.
  implication: The embedded popup is both the observed failure boundary and an unsupported authorization architecture; changing OAuth scopes or secrets will not fix this screen.

## Resolution

root_cause: The frontend creates the Google consent window with window.open from inside the Codex in-app browser. That popup remains part of the embedded webview/user-agent, while Google OAuth explicitly disallows embedded user-agents. The backend-generated URL and local Web OAuth configuration are valid; Google serves the page normally outside that container.
fix: Added a local-only POST endpoint that obtains the existing authorization URL and opens it with the operating system default browser. The frontend calls that endpoint instead of assigning the URL to window.open, displays a continue-in-browser notice, and polls /api/v1/auth/google/status until connected or timed out. The existing callback and start endpoint remain available.
verification: Backend suite passes 51 tests, including guarded system-browser launch coverage; the frontend production build passes; and the restarted live backend served the launch preflight and POST with 200 followed by status polling. The personal-account connected state awaits the user's one-time consent, which cannot be automated or entered by the agent.
files_changed: [backend/api.py, backend/tests/test_api.py, frontend/app/lib/aether-api.ts, frontend/app/page.tsx, frontend/app/globals.css]
