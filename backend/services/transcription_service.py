"""Dedicated speech-to-text providers for short ElaraX voice commands."""

from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Optional

import requests

from backend.config import (
    GROQ_TRANSCRIPTION_MODEL,
    GROQ_TRANSCRIPTION_TIMEOUT_SECONDS,
    WHISPER_ALLOW_DOWNLOAD,
    WHISPER_CACHE_DIR,
    WHISPER_LANGUAGE,
    WHISPER_MODEL,
)
from backend.services.gemini_reasoning_service import (
    GeminiReasoningService,
    gemini_reasoning_service,
)


_MIME_SUFFIXES = {
    "audio/wav": ".wav",
    "audio/mp3": ".mp3",
    "audio/mpeg": ".mp3",
    "audio/aiff": ".aiff",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/m4a": ".m4a",
    "audio/mp4": ".mp4",
    "audio/opus": ".opus",
    "audio/webm": ".webm",
}

_WHISPER_INITIAL_PROMPT = (
    "ElaraX voice command. Preserve imperative verbs such as send, draft, compose, "
    "show, read, find, check, schedule, create, move, and turn. Preserve names, "
    "numbers, email addresses, and message wording."
)

_GROQ_TRANSCRIPTION_PROMPT = (
    "ElaraX voice command transcript. Preserve imperative verbs such as send, draft, compose, "
    "show, read, find, check, schedule, create, move, and turn. Preserve names, numbers, email "
    "addresses, alphanumeric identifiers, and exact message wording. Commands may use English, "
    "Bengali, Hindi, or code-mixed speech. Render clearly spoken email forms such as "
    "'name at gmail dot com' as 'name@gmail.com'."
)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


class GroqTranscriptionService:
    """Hosted recorded-command STT using Groq's OpenAI-compatible endpoint."""

    endpoint = "https://api.groq.com/openai/v1/audio/transcriptions"

    def __init__(
        self,
        *,
        model: str = GROQ_TRANSCRIPTION_MODEL,
        timeout_seconds: int = GROQ_TRANSCRIPTION_TIMEOUT_SECONDS,
        enabled: Optional[bool] = None,
        request_post: Callable[..., Any] = requests.post,
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._enabled_override = enabled
        self._request_post = request_post
        self.last_error: Optional[str] = None

    def enabled(self) -> bool:
        if self._enabled_override is not None:
            return self._enabled_override
        if os.getenv("AETHERBOT_TESTING") == "1":
            return False
        return not _env_flag("AETHERBOT_DISABLE_GROQ_STT")

    def _api_key(self) -> Optional[str]:
        if not self.enabled():
            return None
        value = os.getenv("GROQ_API_KEY") or os.getenv("AETHERBOT_GROQ_API_KEY")
        return value.strip() or None if value else None

    def configured(self) -> bool:
        return self._api_key() is not None

    @staticmethod
    def _status_error(status_code: int) -> str:
        if status_code in {401, 403}:
            return "GroqUnavailable: authentication rejected"
        if status_code == 429:
            return "GroqUnavailable: rate limited"
        if status_code == 413:
            return "GroqUnavailable: audio request too large"
        if status_code >= 500:
            return "GroqUnavailable: service unavailable"
        return f"GroqUnavailable: request failed (HTTP {status_code})"

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str,
        language: Optional[str] = None,
    ) -> Optional[str]:
        if not audio_bytes:
            self.last_error = "NoSpeech: the recording was empty"
            return None
        api_key = self._api_key()
        if not api_key:
            self.last_error = "GroqUnavailable: not configured"
            return None

        suffix = _MIME_SUFFIXES.get(mime_type, ".audio")
        try:
            response = self._request_post(
                self.endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
                files={
                    "file": (
                        f"elarax-command{suffix}",
                        audio_bytes,
                        mime_type,
                    )
                },
                data={
                    "model": self.model,
                    "prompt": _GROQ_TRANSCRIPTION_PROMPT,
                    "response_format": "json",
                    "temperature": "0",
                    **(
                        {"language": language}
                        if language in {"en", "bn", "hi"}
                        else {}
                    ),
                },
                timeout=self.timeout_seconds,
            )
        except requests.Timeout:
            self.last_error = "GroqUnavailable: request timed out"
            return None
        except requests.RequestException:
            self.last_error = "GroqUnavailable: network request failed"
            return None
        except Exception as exc:
            self.last_error = f"GroqUnavailable: {type(exc).__name__}"
            return None

        if not 200 <= response.status_code < 300:
            self.last_error = self._status_error(response.status_code)
            return None
        try:
            payload = response.json()
        except (TypeError, ValueError):
            self.last_error = "GroqUnavailable: invalid provider response"
            return None
        transcript = str(payload.get("text") or "").strip() if isinstance(payload, dict) else ""
        if not transcript:
            self.last_error = "NoSpeech: Groq returned an empty transcript"
            return None
        self.last_error = None
        return transcript


class LocalWhisperTranscriptionService:
    """Lazy, cache-first local Whisper inference with no startup model cost."""

    def __init__(
        self,
        *,
        model_name: str = WHISPER_MODEL,
        cache_dir: Path = WHISPER_CACHE_DIR,
        language: Optional[str] = WHISPER_LANGUAGE,
        allow_download: bool = WHISPER_ALLOW_DOWNLOAD,
        enabled: Optional[bool] = None,
    ) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.language = language
        self.allow_download = allow_download
        self._enabled_override = enabled
        self._model: Any = None
        self._device = "cpu"
        self._load_lock = Lock()
        self._inference_lock = Lock()
        self.last_error: Optional[str] = None

    def enabled(self) -> bool:
        if self._enabled_override is not None:
            return self._enabled_override
        if os.getenv("AETHERBOT_TESTING") == "1":
            return False
        return not _env_flag("AETHERBOT_DISABLE_LOCAL_WHISPER")

    @property
    def checkpoint_path(self) -> Path:
        return self.cache_dir / f"{self.model_name}.pt"

    def _availability_error(self) -> Optional[str]:
        if not self.enabled():
            return "local Whisper is disabled"
        if importlib.util.find_spec("whisper") is None:
            return "the openai-whisper package is not installed"
        if shutil.which("ffmpeg") is None:
            return "ffmpeg is not available on PATH"
        if not self.checkpoint_path.is_file() and not self.allow_download:
            return f"the {self.model_name} checkpoint is not cached"
        return None

    def configured(self) -> bool:
        return self._availability_error() is None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is not None:
                return self._model
            import torch
            import whisper

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._model = whisper.load_model(
                self.model_name,
                device=self._device,
                download_root=str(self.cache_dir),
            )
            return self._model

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str,
        language: Optional[str] = None,
    ) -> Optional[str]:
        if not audio_bytes:
            self.last_error = "NoSpeech: the recording was empty"
            return None
        availability_error = self._availability_error()
        if availability_error:
            self.last_error = f"WhisperUnavailable: {availability_error}"
            return None

        audio_path: Optional[Path] = None
        try:
            model = self._load_model()
            suffix = _MIME_SUFFIXES.get(mime_type, ".audio")
            with tempfile.NamedTemporaryFile(prefix="elarax-stt-", suffix=suffix, delete=False) as handle:
                handle.write(audio_bytes)
                audio_path = Path(handle.name)

            with self._inference_lock:
                result = model.transcribe(
                    str(audio_path),
                    language=language if language in {"en", "bn", "hi"} else self.language,
                    task="transcribe",
                    fp16=self._device == "cuda",
                    temperature=0,
                    condition_on_previous_text=False,
                    initial_prompt=_WHISPER_INITIAL_PROMPT,
                    verbose=False,
                )
            transcript = str((result or {}).get("text") or "").strip()
            if not transcript:
                self.last_error = "NoSpeech: Whisper returned an empty transcript"
                return None
            self.last_error = None
            return transcript
        except Exception as exc:
            self.last_error = f"WhisperUnavailable: {type(exc).__name__}"
            return None
        finally:
            if audio_path is not None:
                try:
                    audio_path.unlink(missing_ok=True)
                except OSError:
                    pass


class VoiceTranscriptionService:
    """Try low-latency hosted STT first, keeping CPU Whisper as final fallback."""

    def __init__(
        self,
        *,
        groq_provider: GroqTranscriptionService,
        cloud_provider: GeminiReasoningService,
        local_provider: LocalWhisperTranscriptionService,
    ) -> None:
        self.groq_provider = groq_provider
        self.local_provider = local_provider
        self.cloud_provider = cloud_provider
        self.last_error: Optional[str] = None
        self.last_provider: Optional[str] = None

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str,
        language: Optional[str] = None,
    ) -> Optional[str]:
        failures: list[str] = []
        heard_no_speech = False
        self.last_provider = None

        def call_provider(provider: Any) -> Optional[str]:
            try:
                return provider.transcribe_audio(audio_bytes, mime_type, language)
            except TypeError:
                # Keep compatibility with injected providers using the
                # original two-argument interface.
                return provider.transcribe_audio(audio_bytes, mime_type)

        if self.groq_provider.configured():
            groq_transcript = call_provider(self.groq_provider)
            if groq_transcript:
                self.last_error = None
                self.last_provider = "groq"
                return groq_transcript
            groq_error = self.groq_provider.last_error or "Groq returned no transcript"
            heard_no_speech = groq_error.startswith("NoSpeech:")
            failures.append(f"groq: {groq_error}")
        else:
            failures.append("groq: not configured")

        if self.cloud_provider.configured():
            cloud_transcript = call_provider(self.cloud_provider)
            if cloud_transcript:
                self.last_error = None
                self.last_provider = "gemini"
                return cloud_transcript
            cloud_error = self.cloud_provider.last_error or "Gemini returned no transcript"
            heard_no_speech = heard_no_speech or cloud_error.startswith("NoSpeech:")
            failures.append(f"gemini: {cloud_error}")
        else:
            failures.append("gemini: not configured")

        local_transcript = call_provider(self.local_provider)
        if local_transcript:
            self.last_error = None
            self.last_provider = "local-whisper"
            return local_transcript
        local_error = self.local_provider.last_error or "Whisper returned no transcript"
        heard_no_speech = heard_no_speech or local_error.startswith("NoSpeech:")
        failures.append(f"local-whisper: {local_error}")

        prefix = "NoSpeech" if heard_no_speech else "TranscriptionUnavailable"
        self.last_error = f"{prefix}: {'; '.join(failures)}"
        return None


groq_transcription_service = GroqTranscriptionService()
local_whisper_transcription_service = LocalWhisperTranscriptionService()
voice_transcription_service = VoiceTranscriptionService(
    groq_provider=groq_transcription_service,
    cloud_provider=gemini_reasoning_service,
    local_provider=local_whisper_transcription_service,
)
