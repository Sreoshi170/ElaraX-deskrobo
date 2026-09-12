---
status: resolved
trigger: "Google OAuth shows Access blocked: DeskRobo can only be used within its organization. Error 403: org_internal when signing in with a personal Gmail account."
created: 2026-08-28T00:00:00+05:30
updated: 2026-09-05T19:25:00+05:30
---

## Current Focus

hypothesis: Confirmed: project deskrobo has an Internal OAuth audience and rejects the personal Gmail account because it is outside the project's parent organization.
test: Human changes Google Auth Platform audience to External Testing, adds the personal Gmail account as a test user, then starts a fresh authorization from AetherBot.
expecting: org_internal no longer appears; Google shows the consent/unverified-app flow, redirects to localhost:8000, and AetherBot reports connected.
next_action: None; retain External Testing/test-user settings for this local development account.

## Symptoms

expected: A personal Gmail account can authorize DeskRobo/AetherBot and the callback stores credentials.
actual: The system browser renders Google's authorization page, but access is blocked before consent.
errors: "Access blocked: DeskRobo can only be used within its organization" and "Error 403: org_internal".
reproduction: From http://localhost:3000 click Connect Google, then attempt to sign in with the personal @gmail.com account shown in the screenshot.
started: First appeared after the embedded-popup issue was fixed and real Google authorization was reached for the first time.

## Eliminated

## Evidence

- timestamp: 2026-08-28T14:30:00+05:30
  checked: Local secrets directory.
  found: secrets/google_oauth_client.json exists and is a local credential JSON file.
  implication: The OAuth flow is using a supplied Google Cloud OAuth client; its non-secret metadata can identify the client type/project while the org_internal decision remains a server-side project setting.
- timestamp: 2026-08-28T14:31:00+05:30
  checked: First safe metadata parsing command.
  found: The command failed at PowerShell parsing before reading or printing any JSON values.
  implication: No credential data was exposed; retry with corrected syntax.
- timestamp: 2026-08-28T14:32:00+05:30
  checked: Non-secret fields from secrets/google_oauth_client.json.
  found: The credential is a Web application OAuth client in project deskrobo with redirect URI http://localhost:8000/api/v1/auth/google/callback.
  implication: The client and local callback type are correct enough to reach Google; the rejection is tied to the OAuth project's server-side audience policy, not a malformed local redirect URI.
- timestamp: 2026-08-28T14:35:00+05:30
  checked: Google's official Manage App Audience documentation.
  found: Google states that External apps are available to any Google Account; Internal apps are limited to members of the Cloud project's parent organization; org_internal is returned when a user outside that parent requests authorization.
  implication: The screenshot exactly matches an Internal audience rejecting a consumer Gmail account. This confirms the root cause independently of local code.
- timestamp: 2026-08-28T14:35:00+05:30
  checked: Google's official Workspace OAuth consent configuration guide and verification exemption documentation.
  found: External Testing apps require explicitly adding test users; personal-use apps under 100 users can continue without verification, though an unverified-app warning and testing limits apply. Internal apps cannot be used by accounts outside the Workspace/Cloud Identity organization.
  implication: For this single personal Gmail account, the intended setup is External + Testing + the Gmail address as a test user, not Internal and not necessarily production verification.
- timestamp: 2026-08-28T14:39:00+05:30
  checked: Official Google documentation on changing user type.
  found: Google documents a Make external action for projects whose OAuth user type is Internal, and separately documents switching back from Internal to External. Resource Manager guidance explicitly says an Internal OAuth consent screen can be updated to External.
  implication: The existing deskrobo project/client can normally be retained; creating a new client JSON is unnecessary if the project's Audience page offers Make external and the user has permission to change it.
- timestamp: 2026-08-28T14:41:00+05:30
  checked: OAuth scope constants in backend/services/google_auth_service.py.
  found: The app requests openid, userinfo.email, gmail.readonly, gmail.compose, calendar.events, and calendar.freebusy.
  implication: This is not identity-only OAuth. In External Testing, the personal Gmail address must be explicitly added as a test user, and Google's testing-mode lifetime rules apply.
- timestamp: 2026-08-28T14:45:00+05:30
  checked: Official Gmail scope classification and Google External Testing limits.
  found: gmail.readonly and gmail.compose are Restricted scopes. External Testing authorizations that request scopes beyond basic identity expire after seven days, including offline refresh tokens.
  implication: External Testing is appropriate for immediate personal/local development, but the user should expect to reconnect weekly. Broader or long-lived production distribution would require OAuth verification and, because restricted Gmail scopes are used, potentially Google's additional restricted-scope requirements.

## Resolution

root_cause: Google Cloud project deskrobo's OAuth audience is configured as Internal. Google rejects the consumer Gmail account before callback because it is not a member of the project's parent Workspace/Cloud Identity organization, producing org_internal.
fix: In Google Cloud Console select project deskrobo, open Google Auth Platform > Audience, choose Make external, retain/select Testing, add the intended personal Gmail address under Test users, and save. If Make external is unavailable due to permissions or organization policy, create a new project while signed in with the personal Gmail account, configure External Testing, add that account as a test user, enable Gmail API and Google Calendar API, create a Web application client with http://localhost:8000/api/v1/auth/google/callback, replace secrets/google_oauth_client.json, and restart the backend.
verification: On 2026-09-05, the restarted local API returned `mode=google` and the live ElaraX dashboard reported Google connected with Gmail and Calendar data rendered; no OAuth error was present. This confirms the personal-account round trip completed successfully.
files_changed:
  - .planning/debug/google-oauth-org-internal.md
