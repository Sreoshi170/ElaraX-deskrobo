"""Robot validation and simulation nodes."""

from backend.graphs.state import AetherBotState
from backend.services.mock_robot_service import execute_mock_command, get_mock_status


ALLOWED_COMMANDS = {
    "STOP",
    "MOVE_FORWARD",
    "MOVE_BACKWARD",
    "TURN_LEFT",
    "TURN_RIGHT",
    "COME_HERE",
    "LOOK_AT_USER",
    "GET_STATUS",
}


def prepare_robot_command_node(state: AetherBotState) -> AetherBotState:
    intent = state.get("intent") or "STATUS"
    command_name = "GET_STATUS" if intent == "STATUS" else intent
    command = state.get("robot_command") or {"command": command_name, "parameters": {}}
    if command.get("command") not in ALLOWED_COMMANDS:
        return {"error": "Unsupported robot command.", "robot_command": None}
    return {"robot_command": command}


def robot_policy_node(state: AetherBotState) -> AetherBotState:
    command = state.get("robot_command")
    if not command or state.get("error"):
        return {}
    if command["command"] == "STOP":
        result = execute_mock_command(command)
        return {
            "robot_status": result,
            "tool_results": {**(state.get("tool_results") or {}), "robot": result},
        }
    if command["command"] == "GET_STATUS":
        status = get_mock_status()
        return {
            "robot_status": status,
            "tool_results": {**(state.get("tool_results") or {}), "robot": status},
        }
    return {
        "pending_action": {"action": "ROBOT_COMMAND", "command": command},
        "requires_confirmation": True,
        "confirmation_status": "pending",
    }


def robot_response_node(state: AetherBotState) -> AetherBotState:
    if state.get("error"):
        return {"final_response": state["error"]}
    command = state.get("robot_command", {}).get("command") if state.get("robot_command") else None
    if command == "STOP" and state.get("robot_status"):
        return {"final_response": "Emergency stop acknowledged by the robot simulator."}
    if command == "GET_STATUS":
        return {"final_response": "Robot status: simulation mode, motion stopped."}
    if state.get("pending_action"):
        return {"final_response": "The robot command is waiting for confirmation and was not executed."}
    return {"final_response": "No robot command was executed."}
