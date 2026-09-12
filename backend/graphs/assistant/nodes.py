"""Non-LLM assistant fallback responses."""

from backend.graphs.state import AetherBotState
from backend.services.gemini_reasoning_service import gemini_reasoning_service
from backend.services.llm_provider import llm_provider_service


_HELP_RESPONSES = {
    "en": (
        "For mock email or connected Gmail, I can check, read, search, summarize, prioritize, list sent/draft/starred mail, "
        "draft or reply, send, forward, mark read or unread, star, archive, move to trash, and delete. "
        "Sending or changing mail always waits for your confirmation."
    ),
    "bn": "আমি মক ইমেইল, ক্যালেন্ডার, ব্রিফিং ও রোবট কমান্ডে সাহায্য করতে পারি।",
    "hi": "मैं मॉक ईमेल, कैलेंडर, ब्रीफिंग और रोबोट कमांड में मदद कर सकता हूँ।",
    "mixed": (
        "For mock email or connected Gmail, I can check, read, search, summarize, prioritize, list sent/draft/starred mail, "
        "draft or reply, send, forward, mark read or unread, star, archive, move to trash, and delete. "
        "Sending or changing mail always waits for your confirmation."
    ),
}


def assistant_response_node(state: AetherBotState) -> AetherBotState:
    language = state.get("response_language") or "en"
    if state.get("supervisor_clarification"):
        return {"final_response": state["supervisor_clarification"]}
    if state.get("intent") == "HELP":
        return {"final_response": _HELP_RESPONSES[language]}
    instruction = (
        "You are ElaraX, a concise multilingual executive assistant. Answer the user directly. "
        "Never claim to have read, sent, scheduled, or moved anything unless a supplied tool result "
        "says so. For email, calendar, or robot actions, tell the user to issue a concrete command "
        "that LangGraph can route safely."
    )
    prompt = f"Reply in language mode '{language}'. User: {state.get('raw_input') or ''}"
    answer = llm_provider_service.generate_text(
        instruction=instruction,
        prompt=prompt,
        max_output_tokens=700,
    ) or gemini_reasoning_service.generate_text(
        instruction=instruction,
        prompt=prompt,
        max_output_tokens=700,
    )
    if answer:
        return {"final_response": answer}
    return {
        "final_response": (
            "The general AI assistant is not connected yet. "
            "Email, calendar, briefing, and robot simulation are available."
        )
    }
