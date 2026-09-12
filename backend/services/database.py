"""SQLite connection and schema helpers for ElaraX persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path


PROFILE_COLUMNS = (
    "full_name",
    "email",
    "phone",
    "country",
    "timezone",
    "occupation",
    "company_name",
    "website",
    "industry",
    "company_size",
    "business_stage",
    "business_model",
    "revenue_model",
    "products_services",
    "target_customers",
    "goals",
    "challenges",
    "business_context",
)


def open_database(path: Path) -> sqlite3.Connection:
    """Open a configured SQLite database and ensure its parent exists."""

    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create the account and session tables when they do not exist."""

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            phone TEXT NOT NULL DEFAULT '',
            country TEXT NOT NULL DEFAULT '',
            timezone TEXT NOT NULL DEFAULT '',
            occupation TEXT NOT NULL,
            company_name TEXT NOT NULL,
            website TEXT NOT NULL DEFAULT '',
            industry TEXT NOT NULL,
            company_size TEXT NOT NULL DEFAULT '',
            business_stage TEXT NOT NULL DEFAULT '',
            business_model TEXT NOT NULL,
            revenue_model TEXT NOT NULL DEFAULT '',
            products_services TEXT NOT NULL DEFAULT '',
            target_customers TEXT NOT NULL DEFAULT '',
            goals TEXT NOT NULL DEFAULT '',
            challenges TEXT NOT NULL DEFAULT '',
            business_context TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

        CREATE TABLE IF NOT EXISTS activity_records (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            activity_type TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'completed',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_activity_user_created
            ON activity_records(user_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS database_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    connection.commit()
