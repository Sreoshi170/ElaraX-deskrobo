"""Consistent, keyless Microsoft neural TTS fallback for ElaraX."""

import asyncio
import io
import tempfile
from pathlib import Path
from typing import Optional

from backend.nodes.language_node import detect_language


class EdgeTtsService:
    """Synthesize speech with one pinned Edge neural voice per ElaraX language."""

    MIME_TYPE = "audio/mpeg"
    VOICES = {
        "en": "en-IN-PrabhatNeural",
        "bn": "bn-IN-BashkarNeural",
        "hi": "hi-IN-MadhurNeural",
        # Code-mixed replies use the stable English India voice as the bridge voice.
        "mixed": "en-IN-PrabhatNeural",
    }

    def __init__(self, *, connect_timeout: int = 10, receive_timeout: int = 60) -> None:
        self.connect_timeout = connect_timeout
        self.receive_timeout = receive_timeout
        self.last_error: Optional[str] = None

    @classmethod
    def language_key(cls, text: str, language: Optional[str] = None) -> str:
        """Normalize an ElaraX language code, detecting it when no code is supplied."""

        candidate = (language or "").strip().casefold()
        if candidate == "mixed":
            return "mixed"
        for language_key in ("bn", "hi", "en"):
            if candidate == language_key or candidate.startswith(f"{language_key}-"):
                return language_key
        detected = detect_language(text)
        return detected if detected in cls.VOICES else "en"

    @classmethod
    def voice_for_language(cls, text: str, language: Optional[str] = None) -> str:
        return cls.VOICES[cls.language_key(text, language)]

    def synthesize_speech(self, text: str, language: Optional[str] = None) -> Optional[bytes]:
        """Return an MP3 response with neural Edge, then a gTTS fallback.

        Both providers are optional and keyless. The fallback keeps Hindi and
        Bengali speech available when Edge's websocket endpoint is blocked by
        a local network while the browser remains the final client fallback.
        """

        clean_text = " ".join(text.strip().split())[:3_000]
        if not clean_text:
            self.last_error = "EmptyText: Edge speech generation received no text."
            return None

        language_key = self.language_key(clean_text, language)
        voice = self.VOICES[language_key]
        try:
            import edge_tts

            with tempfile.TemporaryDirectory(prefix="elarax-edge-tts-") as temporary_directory:
                output_path = Path(temporary_directory) / "speech.mp3"
                communicator = edge_tts.Communicate(
                    clean_text,
                    voice=voice,
                    rate="+0%",
                    volume="+0%",
                    pitch="+0Hz",
                    connect_timeout=self.connect_timeout,
                    receive_timeout=self.receive_timeout,
                )
                asyncio.run(communicator.save(str(output_path)))
                audio_bytes = output_path.read_bytes()

            if not audio_bytes:
                self.last_error = "EmptyAudio: Edge speech generation returned no audio."
                return None
            self.last_error = None
            return audio_bytes
        except Exception as exc:  # provider boundary; browser speech is the final fallback
            edge_error = f"{type(exc).__name__}: Edge speech generation was unavailable."
            try:
                from gtts import gTTS

                output = io.BytesIO()
                gTTS(
                    text=clean_text,
                    lang={"en": "en", "hi": "hi", "bn": "bn", "mixed": "en"}[language_key],
                    tld="co.in",
                ).write_to_fp(output)
                audio_bytes = output.getvalue()
                if audio_bytes:
                    self.last_error = None
                    return audio_bytes
            except Exception as fallback_exc:
                self.last_error = (
                    f"{edge_error} {type(fallback_exc).__name__}: gTTS speech generation was unavailable."
                )
            return None


edge_tts_service = EdgeTtsService()
