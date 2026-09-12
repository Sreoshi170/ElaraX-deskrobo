"""Google OAuth flow and encrypted local credential persistence."""

import json
import os
import secrets
import time
from pathlib import Path
from threading import RLock
from typing import Any, Optional

import requests
from cryptography.fernet import Fernet, InvalidToken
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from backend.config import (
    GOOGLE_CLIENT_FILE,
    GOOGLE_REDIRECT_URI,
    GOOGLE_TOKEN_FILE,
    TOKEN_ENCRYPTION_KEY_FILE,
)


GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.freebusy",
]


class GoogleIntegrationError(RuntimeError):
    """A safe, user-displayable Google integration failure."""


class GoogleNotConnectedError(GoogleIntegrationError):
    """Raised when an authenticated Google operation is requested too early."""


class EncryptedTokenStore:
    """Persist an OAuth credential JSON document with local symmetric encryption."""

    def __init__(self, token_path: Path, key_path: Path) -> None:
        self.token_path = token_path
        self.key_path = key_path

    def exists(self) -> bool:
        return self.token_path.is_file()

    def _fernet(self) -> Fernet:
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        if self.key_path.exists():
            key = self.key_path.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            self.key_path.write_bytes(key)
            try:
                self.key_path.chmod(0o600)
            except OSError:
                pass
        return Fernet(key)

    def save(self, credentials: Credentials) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = self._fernet().encrypt(credentials.to_json().encode("utf-8"))
        temporary_path = self.token_path.with_suffix(".tmp")
        temporary_path.write_bytes(encrypted)
        temporary_path.replace(self.token_path)
        try:
            self.token_path.chmod(0o600)
        except OSError:
            pass

    def load(self) -> Credentials:
        if not self.token_path.exists():
            raise GoogleNotConnectedError("Connect your Google account first.")
        try:
            decrypted = self._fernet().decrypt(self.token_path.read_bytes())
            info = json.loads(decrypted.decode("utf-8"))
            return Credentials.from_authorized_user_info(info, GOOGLE_SCOPES)
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            raise GoogleIntegrationError(
                "The saved Google connection could not be opened. Disconnect and connect it again."
            ) from exc

    def clear(self) -> None:
        if self.token_path.exists():
            self.token_path.unlink()


class GoogleAuthManager:
    """Own the single-user local OAuth lifecycle."""

    def __init__(
        self,
        client_file: Path = GOOGLE_CLIENT_FILE,
        redirect_uri: str = GOOGLE_REDIRECT_URI,
        token_store: Optional[EncryptedTokenStore] = None,
    ) -> None:
        self.client_file = client_file
        self.redirect_uri = redirect_uri
        self.token_store = token_store or EncryptedTokenStore(
            GOOGLE_TOKEN_FILE, TOKEN_ENCRYPTION_KEY_FILE
        )
        self._lock = RLock()
        self._oauth_states: dict[str, tuple[Flow, float]] = {}

    def _validate_client(self) -> None:
        if not self.client_file.is_file():
            raise GoogleIntegrationError(
                "Google OAuth configuration is missing from the local secrets folder."
            )
        try:
            document = json.loads(self.client_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GoogleIntegrationError("The Google OAuth configuration is not valid JSON.") from exc

        client = document.get("web")
        if not isinstance(client, dict):
            raise GoogleIntegrationError(
                "Create a Google OAuth client of type Web application and download it again."
            )
        if not client.get("client_id") or not client.get("client_secret"):
            raise GoogleIntegrationError("The Google OAuth client is incomplete.")
        redirect_uris = client.get("redirect_uris") or []
        if self.redirect_uri not in redirect_uris:
            raise GoogleIntegrationError(
                f"Add this exact authorized redirect URI in Google Cloud: {self.redirect_uri}"
            )

    def _new_flow(self, state: Optional[str] = None) -> Flow:
        self._validate_client()
        if self.redirect_uri.startswith(("http://localhost", "http://127.0.0.1")):
            os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
        flow = Flow.from_client_secrets_file(
            str(self.client_file),
            scopes=GOOGLE_SCOPES,
            state=state,
        )
        flow.redirect_uri = self.redirect_uri
        return flow

    def begin_authorization(self) -> str:
        with self._lock:
            now = time.time()
            # Expire stale pending flows
            self._oauth_states = {
                state: (flow, created)
                for state, (flow, created) in self._oauth_states.items()
                if now - created < 600
            }
            state = secrets.token_urlsafe(32)
            flow = self._new_flow(state=state)
            authorization_url, returned_state = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
            )
            self._oauth_states[returned_state] = (flow, now)
            return authorization_url

    def complete_authorization(self, state: str, authorization_response: str) -> Credentials:
        with self._lock:
            entry = self._oauth_states.pop(state, None)
            if entry is None or time.time() - entry[1] > 600:
                raise GoogleIntegrationError("The Google sign-in request expired. Start it again.")
            flow = entry[0]
            try:
                flow.fetch_token(authorization_response=authorization_response)
            except Exception as exc:
                raise GoogleIntegrationError("Google sign-in could not be completed.") from exc
            credentials = flow.credentials
            if not credentials.refresh_token and self.token_store.exists():
                previous = self.token_store.load()
                credentials.refresh_token = previous.refresh_token
            if not credentials.refresh_token:
                raise GoogleIntegrationError(
                    "Google did not return offline access. Revoke ElaraX access and connect again."
                )
            self.token_store.save(credentials)
            return credentials

    def has_saved_connection(self) -> bool:
        if os.getenv("AETHERBOT_TESTING") == "1":
            return False
        return self.token_store.exists()

    def get_credentials(self) -> Credentials:
        with self._lock:
            credentials = self.token_store.load()
            if credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except RefreshError as exc:
                    raise GoogleIntegrationError(
                        "Google access expired. Disconnect and connect your account again."
                    ) from exc
                self.token_store.save(credentials)
            if not credentials.valid:
                raise GoogleNotConnectedError("Connect your Google account first.")
            return credentials

    def revoke_and_clear(self) -> None:
        with self._lock:
            if not self.token_store.exists():
                return
            try:
                credentials = self.token_store.load()
                token = credentials.refresh_token or credentials.token
                if token:
                    requests.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": token},
                        headers={"content-type": "application/x-www-form-urlencoded"},
                        timeout=10,
                    )
            finally:
                self.token_store.clear()

    def connection_summary(self) -> dict[str, Any]:
        if not self.has_saved_connection():
            return {"connected": False, "email": None, "scopes": []}
        try:
            credentials = self.get_credentials()
        except GoogleIntegrationError as exc:
            return {"connected": False, "email": None, "scopes": [], "error": str(exc)}
        return {
            "connected": True,
            "email": None,
            "scopes": sorted(credentials.granted_scopes or credentials.scopes or []),
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
        }


google_auth_manager = GoogleAuthManager()
