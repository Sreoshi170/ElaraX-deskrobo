"""Tests for the locally persisted email action-item store."""

from pathlib import Path

import pytest

from backend.services.action_item_service import ActionItemService


def test_action_items_dedupe_by_source_email_and_survive_reload(tmp_path: Path) -> None:
    items_file = tmp_path / "action-items.json"
    service = ActionItemService(items_file=items_file)
    extracted = [
        {"description": "Send the invoice", "due_date": "Friday"},
        {"description": "Send the invoice", "due_date": "Friday"},
    ]

    added = service.add_items("email-1", "Invoice follow-up", extracted)
    duplicate = service.add_items("email-1", "Invoice follow-up", extracted)
    reloaded = ActionItemService(items_file=items_file)

    assert len(added) == 1
    assert duplicate == []
    assert reloaded.list_items(status="open")[0]["description"] == "Send the invoice"


def test_complete_item_persists_done_status(tmp_path: Path) -> None:
    items_file = tmp_path / "action-items.json"
    service = ActionItemService(items_file=items_file)
    item = service.add_items("email-2", "Review request", [{"description": "Review the contract"}])[0]

    completed = service.complete_item(item["id"])
    reloaded = ActionItemService(items_file=items_file)

    assert completed["status"] == "done"
    assert reloaded.list_items(status="open") == []
    assert reloaded.list_items(status="done")[0]["id"] == item["id"]


def test_complete_item_requires_a_known_id(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        ActionItemService(items_file=tmp_path / "action-items.json").complete_item("missing")
