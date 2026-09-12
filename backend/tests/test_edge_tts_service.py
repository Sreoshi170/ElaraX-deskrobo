"""Tests for the deterministic, keyless Edge TTS fallback."""

import sys
import types

from backend.services.edge_tts_service import EdgeTtsService


def test_language_detection_reuses_elarax_language_classifier() -> None:
    service = EdgeTtsService()

    assert service.language_key("amar important email bolo") == "bn"
    assert service.language_key("aaj meri meeting kya hai") == "hi"
    assert service.language_key("Show my calendar") == "en"


def test_explicit_language_codes_are_normalized_to_pinned_voices() -> None:
    service = EdgeTtsService()

    assert service.voice_for_language("anything", "bn-IN") == "bn-IN-BashkarNeural"
    assert service.voice_for_language("anything", "hi") == "hi-IN-MadhurNeural"
    assert service.voice_for_language("anything", "mixed") == "en-IN-PrabhatNeural"


def test_synthesis_uses_selected_voice_and_returns_saved_audio(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeCommunicate:
        def __init__(self, text: str, **kwargs: object) -> None:
            calls.append({"text": text, **kwargs})

        async def save(self, output_path: str) -> None:
            with open(output_path, "wb") as output_file:
                output_file.write(b"ID3 fake edge audio")

    monkeypatch.setitem(sys.modules, "edge_tts", types.SimpleNamespace(Communicate=FakeCommunicate))
    service = EdgeTtsService()

    audio = service.synthesize_speech("amar important email bolo", "bn")

    assert audio == b"ID3 fake edge audio"
    assert calls == [
        {
            "text": "amar important email bolo",
            "voice": "bn-IN-BashkarNeural",
            "rate": "+0%",
            "volume": "+0%",
            "pitch": "+0Hz",
            "connect_timeout": 10,
            "receive_timeout": 60,
        }
    ]
    assert service.last_error is None
