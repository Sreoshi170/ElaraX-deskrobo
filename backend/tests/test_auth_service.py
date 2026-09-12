import json
import sqlite3

import backend.services.auth_service as auth_service


def _profile(email: str = "owner@example.com") -> dict[str, str]:
    return {
        "full_name": "Demo Owner",
        "email": email,
        "phone": "+91 98765 43210",
        "country": "India",
        "timezone": "Asia/Calcutta",
        "occupation": "Founder",
        "company_name": "Demo Company",
        "website": "https://demo.example.com",
        "industry": "Software",
        "company_size": "1-10",
        "business_stage": "Early stage",
        "business_model": "SaaS subscription",
        "revenue_model": "Monthly subscriptions",
        "products_services": "Business planning software",
        "target_customers": "Startup founders",
        "goals": "Reach 100 customers",
        "challenges": "Customer acquisition",
        "business_context": "A demo company building planning tools for founders.",
    }


def test_auth_persists_users_and_sessions_in_sqlite(tmp_path, monkeypatch) -> None:
    database = tmp_path / "elarax.sqlite3"
    monkeypatch.setattr(auth_service, "AUTH_DATABASE_FILE", database)
    monkeypatch.setattr(auth_service, "AUTH_USERS_FILE", tmp_path / "users.json")
    monkeypatch.setattr(auth_service, "AUTH_SESSIONS_FILE", tmp_path / "sessions.json")

    created = auth_service.create_user(_profile(), "StrongPass123")
    token, signed_in = auth_service.authenticate("OWNER@example.com", "StrongPass123")

    assert signed_in["id"] == created["id"]
    assert auth_service.user_from_token(token)["profile"]["company_name"] == "Demo Company"

    updated = auth_service.update_profile(
        created["id"],
        {**_profile(), "goals": "Reach 250 customers"},
    )
    assert updated["profile"]["goals"] == "Reach 250 customers"

    auth_service.revoke_session(token)
    assert auth_service.user_from_token(token) is None

    connection = sqlite3.connect(database)
    assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    connection.close()


def test_legacy_json_users_are_migrated_once(tmp_path, monkeypatch) -> None:
    database = tmp_path / "elarax.sqlite3"
    users_file = tmp_path / "users.json"
    sessions_file = tmp_path / "auth_sessions.json"
    monkeypatch.setattr(auth_service, "AUTH_DATABASE_FILE", database)
    monkeypatch.setattr(auth_service, "AUTH_USERS_FILE", users_file)
    monkeypatch.setattr(auth_service, "AUTH_SESSIONS_FILE", sessions_file)

    user_id = "legacy-user"
    users_file.write_text(
        json.dumps(
            {
                user_id: {
                    "id": user_id,
                    **_profile("legacy@example.com"),
                    "password_hash": auth_service._hash_password("LegacyPass123"),
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                }
            }
        ),
        encoding="utf-8",
    )

    token, user = auth_service.authenticate("legacy@example.com", "LegacyPass123")

    assert user["id"] == user_id
    assert auth_service.user_from_token(token)["profile"]["company_name"] == "Demo Company"
