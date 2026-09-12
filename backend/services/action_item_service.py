"""Small, locally persisted action-item store populated from email content."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Iterable, Optional
from uuid import uuid4

from backend.config import ACTION_ITEMS_FILE


class ActionItemService:
    """Persist extracted email follow-ups without involving an external service."""

    def __init__(self, *, items_file: Path = ACTION_ITEMS_FILE) -> None:
        self.items_file = items_file
        self._lock = RLock()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_locked(self) -> list[dict[str, Any]]:
        try:
            loaded = json.loads(self.items_file.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(loaded, list):
            return []

        items: list[dict[str, Any]] = []
        for raw in loaded:
            if not isinstance(raw, dict):
                continue
            item_id = str(raw.get("id") or "").strip()
            description = str(raw.get("description") or "").strip()
            source_email_id = str(raw.get("source_email_id") or "").strip()
            if not item_id or not description or not source_email_id:
                continue
            items.append(
                {
                    "id": item_id,
                    "description": description,
                    "due_date": str(raw.get("due_date") or "").strip() or None,
                    "source_email_id": source_email_id,
                    "source_subject": str(raw.get("source_subject") or "").strip(),
                    "status": "done" if raw.get("status") == "done" else "open",
                    "created_at": str(raw.get("created_at") or self._now()),
                }
            )
        return items

    def _save_locked(self, items: list[dict[str, Any]]) -> None:
        self.items_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = self.items_file.with_suffix(".tmp")
        temporary_file.write_text(json.dumps(items, indent=2, sort_keys=True), encoding="utf-8")
        temporary_file.replace(self.items_file)

    @staticmethod
    def _copy_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        return [dict(item) for item in items]

    def list_items(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        if status is not None and status not in {"open", "done"}:
            raise ValueError("Action-item status must be open or done.")
        with self._lock:
            items = self._load_locked()
            if status is not None:
                items = [item for item in items if item["status"] == status]
            return self._copy_items(items)

    def add_items(
        self,
        email_id: str,
        subject: str,
        items: Iterable[Any],
    ) -> list[dict[str, Any]]:
        """Add one email's extracted tasks once, even when that email is re-fetched."""

        source_email_id = str(email_id or "").strip()
        if not source_email_id:
            return []
        with self._lock:
            stored = self._load_locked()
            if any(item["source_email_id"] == source_email_id for item in stored):
                return []

            added: list[dict[str, Any]] = []
            seen_descriptions: set[str] = set()
            for extracted in items:
                if hasattr(extracted, "description"):
                    description = str(getattr(extracted, "description") or "").strip()
                    due_date = getattr(extracted, "due_date", None)
                elif isinstance(extracted, dict):
                    description = str(extracted.get("description") or "").strip()
                    due_date = extracted.get("due_date")
                else:
                    continue
                if not description or description.casefold() in seen_descriptions:
                    continue
                seen_descriptions.add(description.casefold())
                added.append(
                    {
                        "id": f"action-{uuid4().hex}",
                        "description": description,
                        "due_date": str(due_date or "").strip() or None,
                        "source_email_id": source_email_id,
                        "source_subject": str(subject or "").strip(),
                        "status": "open",
                        "created_at": self._now(),
                    }
                )
            if added:
                stored.extend(added)
                self._save_locked(stored)
            return self._copy_items(added)

    def complete_item(self, item_id: str) -> dict[str, Any]:
        """Mark an item done and persist it; completing an item is idempotent."""

        clean_id = str(item_id or "").strip()
        with self._lock:
            stored = self._load_locked()
            for item in stored:
                if item["id"] == clean_id:
                    if item["status"] != "done":
                        item["status"] = "done"
                        self._save_locked(stored)
                    return dict(item)
        raise KeyError(clean_id)


action_item_service = ActionItemService()
