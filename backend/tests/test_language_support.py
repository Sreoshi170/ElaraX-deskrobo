"""Multilingual input contract tests."""

from backend.nodes.intent_node import _classify
from backend.nodes.language_node import detect_language, language_node


def test_detects_supported_scripts_and_romanized_commands() -> None:
    assert detect_language("Show my emails") == "en"
    assert detect_language("\u0906\u091c \u092e\u0947\u0930\u0947 \u0908\u092e\u0947\u0932 \u0926\u093f\u0916\u093e\u0913") == "hi"
    assert detect_language("\u0986\u099c \u0986\u09ae\u09be\u09b0 \u0987\u09ae\u09c7\u09b2 \u09a6\u09c7\u0996\u09be\u0993") == "bn"
    assert detect_language("aaj mere emails dikhao") == "hi"
    assert detect_language("amar emails dekhao") == "bn"


def test_explicit_language_hint_overrides_detection() -> None:
    result = language_node({"raw_input": "Show my emails", "language_hint": "bn"})
    assert result["input_language"] == "bn"
    assert result["response_language"] == "bn"


def test_hindi_and_bengali_commands_route_to_specialists() -> None:
    assert _classify("\u0906\u091c \u092e\u0947\u0930\u0947 \u0908\u092e\u0947\u0932 \u0926\u093f\u0916\u093e\u0913") == "CHECK_EMAIL"
    assert _classify("\u0986\u099c \u0986\u09ae\u09be\u09b0 \u0987\u09ae\u09c7\u09b2 \u09a6\u09c7\u0996\u09be\u0993") == "CHECK_EMAIL"
    assert _classify("\u0986\u09ae\u09be\u09a6\u09c7\u09b0 \u09ac\u09be\u099c\u09be\u09b0 \u09a8\u09bf\u09df\u09c7 \u0997\u09ac\u09c7\u09b7\u09a3\u09be") == "MARKET_RESEARCH"
