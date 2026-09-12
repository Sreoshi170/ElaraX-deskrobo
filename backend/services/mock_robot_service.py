"""Safe robot simulator; no ESP32 connection is made."""

from typing import Any


def execute_mock_command(command: dict[str, Any]) -> dict[str, Any]:
    """Return a simulated acknowledgement for an allowlisted command."""

    return {
        "ok": True,
        "mock": True,
        "command": command["command"],
        "status": "stopped" if command["command"] == "STOP" else "ready",
    }


def get_mock_status() -> dict[str, Any]:
    return {"connected": False, "mode": "simulation", "motion": "stopped"}

