"""Deterministic language detection for ElaraX commands."""

import re

from backend.graphs.state import AetherBotState, LanguageCode


_ROMAN_BENGALI = {
    "ache",
    "ajke",
    "amar",
    "ami",
    "amake",
    "apni",
    "bolo",
    "bolun",
    "chai",
    "kibhabe",
    "keno",
    "kor",
    "koren",
    "koro",
    "korbo",
    "ki",
    "kothay",
    "pathao",
    "pore",
    "porun",
    "thamo",
    "tumi",
}
_ROMAN_HINDI = {
    "aaj",
    "abhi",
    "aap",
    "aapka",
    "aapki",
    "aapko",
    "batao",
    "bataiye",
    "bhejo",
    "dikhao",
    "hai",
    "hain",
    "kaise",
    "kab",
    "kahan",
    "kya",
    "kyun",
    "meri",
    "mera",
    "mere",
    "mujhe",
    "mujhko",
    "ruko",
    "sakta",
    "tum",
    "tumhara",
    "kal",
}


def normalize_language_preference(value: str | None) -> LanguageCode | None:
    """Return a supported forced language, or ``None`` for automatic mode."""

    candidate = (value or "").strip().casefold()
    if candidate in {"", "auto", "detect", "automatic"}:
        return None
    if candidate in {"en", "en-in", "english", "ইংরেজি"}:
        return "en"
    if candidate in {"bn", "bn-in", "bengali", "বাংলা", "bangla"}:
        return "bn"
    if candidate in {"hi", "hi-in", "hindi", "हिंदी", "हिन्दी"}:
        return "hi"
    if candidate in {"mixed", "code-mixed", "hinglish", "banglish"}:
        return "mixed"
    return None


def detect_language(text: str) -> LanguageCode:
    """Detect supported scripts and common romanized command vocabulary."""

    lowered = text.casefold()
    has_bengali = bool(re.search(r"[\u0980-\u09ff]", lowered))
    has_devanagari = bool(re.search(r"[\u0900-\u097f]", lowered))
    has_latin = bool(re.search(r"[a-z]", lowered))

    if has_bengali and (has_devanagari or has_latin):
        return "mixed"
    if has_devanagari and has_latin:
        return "mixed"
    if has_bengali:
        return "bn"
    if has_devanagari:
        return "hi"

    words = set(re.findall(r"[a-z]+", lowered))
    bengali_hits = words & _ROMAN_BENGALI
    hindi_hits = words & _ROMAN_HINDI
    if bengali_hits and hindi_hits:
        return "mixed"
    if bengali_hits:
        return "bn"
    if hindi_hits:
        return "hi"
    return "en"


def language_node(state: AetherBotState) -> AetherBotState:
    """Set input and response language without invoking an LLM."""

    language = normalize_language_preference(state.get("language_hint")) or detect_language(
        state.get("raw_input") or ""
    )
    return {"input_language": language, "response_language": language}
