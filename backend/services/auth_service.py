"""Local account, profile, and session persistence for ElaraX.

Authentication is deliberately kept outside the agent graphs. SQLite provides
transactional storage for the local FastAPI application without requiring a
separate database service. Legacy JSON files are imported once when the
database is first opened.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
from secrets import token_hex, token_urlsafe
from threading import Lock
from typing import Any
from uuid import uuid4

import sqlite3

from backend.config import AUTH_DATABASE_FILE, AUTH_SESSIONS_FILE, AUTH_USERS_FILE
from backend.services.database import (
    PROFILE_COLUMNS,
    initialize_schema,
    open_database,
)


class AuthError(ValueError):
    """A safe, user-facing authentication error."""


PROFILE_FIELDS = PROFILE_COLUMNS

_PASSWORD_ITERATIONS = 310_000
_store_lock = Lock()
_default_auth_database_file = AUTH_DATABASE_FILE
_default_auth_users_file = AUTH_USERS_FILE
_default_auth_sessions_file = AUTH_SESSIONS_FILE


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _database_path() -> Path:
    """Resolve the database path, including isolated test overrides."""

    if AUTH_DATABASE_FILE != _default_auth_database_file:
        return AUTH_DATABASE_FILE
    if (
        AUTH_USERS_FILE != _default_auth_users_file
        or AUTH_SESSIONS_FILE != _default_auth_sessions_file
    ):
        return AUTH_USERS_FILE.with_name(f"{AUTH_USERS_FILE.stem}.sqlite3")
    return AUTH_DATABASE_FILE


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _hash_password(password: str, salt: str | None = None) -> str:
    salt_value = salt or token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_value),
        _PASSWORD_ITERATIONS,
    ).hex()
    return f"{salt_value}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    actual = _hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(actual, expected)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().casefold()


def _public_user(user: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": user["id"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
        "profile": {field: user[field] or "" for field in PROFILE_FIELDS},
    }


def _validate_profile(
    profile: dict[str, Any], *, require_signup_fields: bool = False
) -> dict[str, str]:
    cleaned = {field: str(profile.get(field) or "").strip() for field in PROFILE_FIELDS}
    if require_signup_fields:
        for field, label in (
            ("full_name", "Full name"),
            ("email", "Email"),
            ("occupation", "Occupation"),
            ("company_name", "Business or company name"),
            ("industry", "Industry"),
            ("business_model", "Business model"),
            ("business_context", "Business context"),
        ):
            if not cleaned[field]:
                raise AuthError(f"{label} is required.")
    if cleaned["email"]:
        cleaned["email"] = _normalize_email(cleaned["email"])
        if cleaned["email"].count("@") != 1 or "." not in cleaned["email"].rsplit("@", 1)[-1]:
            raise AuthError("Enter a valid email address.")
    for field, value in cleaned.items():
        if len(value) > 2_000:
            raise AuthError(f"{field.replace('_', ' ').capitalize()} is too long.")
    return cleaned


def _open_database() -> sqlite3.Connection:
    connection = open_database(_database_path())
    initialize_schema(connection)
    _migrate_legacy_json(connection)
    return connection


def _migrate_legacy_json(connection: sqlite3.Connection) -> None:
    marker = connection.execute(
        "SELECT value FROM database_metadata WHERE key = 'legacy_json_migrated'"
    ).fetchone()
    if marker:
        return

    legacy_users = _read_json(AUTH_USERS_FILE, {})
    if isinstance(legacy_users, dict):
        for candidate in legacy_users.values():
            if not isinstance(candidate, dict):
                continue
            user_id = str(candidate.get("id") or uuid4())
            password_hash = str(candidate.get("password_hash") or "")
            email = _normalize_email(str(candidate.get("email") or ""))
            if not password_hash or not email:
                continue
            values = {
                field: str(candidate.get(field) or "").strip()
                for field in PROFILE_FIELDS
            }
            values["email"] = email
            created_at = str(candidate.get("created_at") or _now())
            updated_at = str(candidate.get("updated_at") or created_at)
            columns = (
                "id",
                *PROFILE_FIELDS,
                "password_hash",
                "created_at",
                "updated_at",
            )
            placeholders = ", ".join("?" for _ in columns)
            connection.execute(
                f"INSERT OR IGNORE INTO users ({', '.join(columns)}) VALUES ({placeholders})",
                (
                    user_id,
                    *(values[field] for field in PROFILE_FIELDS),
                    password_hash,
                    created_at,
                    updated_at,
                ),
            )

    legacy_sessions = _read_json(AUTH_SESSIONS_FILE, {})
    if isinstance(legacy_sessions, dict):
        for token, session in legacy_sessions.items():
            if not isinstance(session, dict):
                continue
            user_id = str(session.get("user_id") or "")
            created_at = str(session.get("created_at") or _now())
            if not user_id or not connection.execute(
                "SELECT 1 FROM users WHERE id = ?", (user_id,)
            ).fetchone():
                continue
            connection.execute(
                "INSERT OR IGNORE INTO sessions (token_hash, user_id, created_at) VALUES (?, ?, ?)",
                (_hash_token(str(token)), user_id, created_at),
            )

    connection.execute(
        "INSERT INTO database_metadata (key, value) VALUES ('legacy_json_migrated', ?)",
        (_now(),),
    )
    connection.commit()


def create_user(profile: dict[str, Any], password: str) -> dict[str, Any]:
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")
    cleaned = _validate_profile(profile, require_signup_fields=True)
    with _store_lock:
        connection = _open_database()
        try:
            user_id = str(uuid4())
            timestamp = _now()
            columns = (
                "id",
                *PROFILE_FIELDS,
                "password_hash",
                "created_at",
                "updated_at",
            )
            placeholders = ", ".join("?" for _ in columns)
            connection.execute(
                f"INSERT INTO users ({', '.join(columns)}) VALUES ({placeholders})",
                (
                    user_id,
                    *(cleaned[field] for field in PROFILE_FIELDS),
                    _hash_password(password),
                    timestamp,
                    timestamp,
                ),
            )
            connection.commit()
            user = connection.execute(
                f"SELECT id, {', '.join(PROFILE_FIELDS)}, created_at, updated_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            return _public_user(user)
        except sqlite3.IntegrityError as error:
            connection.rollback()
            if "users.email" in str(error).lower() or "unique" in str(error).lower():
                raise AuthError("An account with that email already exists.") from error
            raise
        finally:
            connection.close()


def authenticate(email: str, password: str) -> tuple[str, dict[str, Any]]:
    normalized = _normalize_email(email)
    with _store_lock:
        connection = _open_database()
        try:
            user = connection.execute(
                f"SELECT id, {', '.join(PROFILE_FIELDS)}, password_hash, created_at, updated_at "
                "FROM users WHERE email = ? COLLATE NOCASE",
                (normalized,),
            ).fetchone()
            if not user or not _verify_password(password, str(user["password_hash"])):
                raise AuthError("Email or password is incorrect.")
            token = token_urlsafe(32)
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, created_at) VALUES (?, ?, ?)",
                (_hash_token(token), user["id"], _now()),
            )
            connection.commit()
            return token, _public_user(user)
        finally:
            connection.close()


def create_session_for_user(user_id: str) -> str:
    with _store_lock:
        connection = _open_database()
        try:
            user = connection.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                raise AuthError("That account no longer exists.")
            token = token_urlsafe(32)
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, created_at) VALUES (?, ?, ?)",
                (_hash_token(token), user_id, _now()),
            )
            connection.commit()
            return token
        finally:
            connection.close()


def user_from_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    with _store_lock:
        connection = _open_database()
        try:
            user = connection.execute(
                f"SELECT u.id, {', '.join(f'u.{field}' for field in PROFILE_FIELDS)}, "
                "u.created_at, u.updated_at "
                "FROM sessions AS s JOIN users AS u ON u.id = s.user_id "
                "WHERE s.token_hash = ?",
                (_hash_token(token),),
            ).fetchone()
            return _public_user(user) if user else None
        finally:
            connection.close()


def update_profile(user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
    with _store_lock:
        connection = _open_database()
        try:
            user = connection.execute(
                f"SELECT id, {', '.join(PROFILE_FIELDS)}, created_at, updated_at "
                "FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not user:
                raise AuthError("That account no longer exists.")
            merged = {field: user[field] or "" for field in PROFILE_FIELDS}
            merged.update(profile)
            cleaned = _validate_profile(merged, require_signup_fields=True)
            duplicate = connection.execute(
                "SELECT id FROM users WHERE email = ? COLLATE NOCASE AND id != ?",
                (cleaned["email"], user_id),
            ).fetchone()
            if duplicate:
                raise AuthError("An account with that email already exists.")
            assignments = ", ".join(f"{field} = ?" for field in PROFILE_FIELDS)
            connection.execute(
                f"UPDATE users SET {assignments}, updated_at = ? WHERE id = ?",
                (*(cleaned[field] for field in PROFILE_FIELDS), _now(), user_id),
            )
            connection.commit()
            updated = connection.execute(
                f"SELECT id, {', '.join(PROFILE_FIELDS)}, created_at, updated_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            return _public_user(updated)
        finally:
            connection.close()


def revoke_session(token: str) -> None:
    if not token:
        return
    with _store_lock:
        connection = _open_database()
        try:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))
            connection.commit()
        finally:
            connection.close()


def record_activity(
    user_id: str,
    activity_type: str,
    title: str,
    detail: str = "",
    status: str = "completed",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist a user-scoped activity entry for the live dashboard."""

    if not user_id:
        return
    with _store_lock:
        connection = _open_database()
        try:
            connection.execute(
                """
                INSERT INTO activity_records
                    (id, user_id, activity_type, title, detail, status, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    user_id,
                    str(activity_type or "system")[:80],
                    str(title or "Activity")[:200],
                    str(detail or "")[:2_000],
                    str(status or "completed")[:40],
                    json.dumps(metadata or {}, ensure_ascii=False),
                    _now(),
                ),
            )
            connection.commit()
        finally:
            connection.close()


def list_activity(user_id: str, limit: int = 40) -> list[dict[str, Any]]:
    """Return the most recent dashboard records for one user."""

    if not user_id:
        return []
    safe_limit = max(1, min(int(limit), 100))
    with _store_lock:
        connection = _open_database()
        try:
            rows = connection.execute(
                """
                SELECT id, activity_type, title, detail, status, metadata_json, created_at
                FROM activity_records
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, safe_limit),
            ).fetchall()
            records: list[dict[str, Any]] = []
            for row in rows:
                try:
                    metadata = json.loads(row["metadata_json"] or "{}")
                except json.JSONDecodeError:
                    metadata = {}
                records.append(
                    {
                        "id": row["id"],
                        "activity_type": row["activity_type"],
                        "title": row["title"],
                        "detail": row["detail"],
                        "status": row["status"],
                        "metadata": metadata if isinstance(metadata, dict) else {},
                        "created_at": row["created_at"],
                    }
                )
            return records
        finally:
            connection.close()
