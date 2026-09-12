"""Offline tests for encrypted Google OAuth credential storage."""

import json

from google.oauth2.credentials import Credentials

from backend.services.google_auth_service import (
    GOOGLE_SCOPES,
    EncryptedTokenStore,
    GoogleAuthManager,
)


def test_encrypted_token_store_round_trip(tmp_path) -> None:
    store = EncryptedTokenStore(tmp_path / "token.enc", tmp_path / "token.key")
    credentials = Credentials(
        token="access-token",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=GOOGLE_SCOPES,
    )

    store.save(credentials)

    assert b"refresh-token" not in store.token_path.read_bytes()
    assert store.load().refresh_token == "refresh-token"
    store.clear()
    assert store.exists() is False


def test_web_oauth_client_generates_authorization_url(tmp_path) -> None:
    redirect_uri = "http://localhost:8000/api/v1/auth/google/callback"
    client_file = tmp_path / "client.json"
    client_file.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "test.apps.googleusercontent.com",
                    "client_secret": "test-secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            }
        ),
        encoding="utf-8",
    )
    manager = GoogleAuthManager(
        client_file=client_file,
        redirect_uri=redirect_uri,
        token_store=EncryptedTokenStore(tmp_path / "token.enc", tmp_path / "key"),
    )

    authorization_url = manager.begin_authorization()

    assert authorization_url.startswith("https://accounts.google.com/")
    assert "access_type=offline" in authorization_url

