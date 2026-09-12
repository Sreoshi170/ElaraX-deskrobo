"""Tests for the dedicated voice transcription provider boundary."""

from pathlib import Path
from types import SimpleNamespace

from backend.services.transcription_service import (
    GroqTranscriptionService,
    LocalWhisperTranscriptionService,
    VoiceTranscriptionService,
)


class FakeProvider:
    def __init__(self, transcript: str | None, error: str | None = None, configured: bool = True):
        self.transcript = transcript
        self.last_error = error
        self.is_configured = configured
        self.calls: list[tuple[bytes, str]] = []

    def configured(self) -> bool:
        return self.is_configured

    def transcribe_audio(self, audio_bytes: bytes, mime_type: str) -> str | None:
        self.calls.append((audio_bytes, mime_type))
        return self.transcript


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


def test_groq_transcription_uses_large_v3_and_context_prompt(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_post(url: str, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse(200, {"text": " Send email to alice@example.com saying hello "})

    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    service = GroqTranscriptionService(
        model="whisper-large-v3",
        timeout_seconds=12,
        enabled=True,
        request_post=fake_post,
    )

    transcript = service.transcribe_audio(b"browser webm bytes", "audio/webm")

    assert transcript == "Send email to alice@example.com saying hello"
    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert call["headers"] == {"Authorization": "Bearer test-groq-key"}
    assert call["files"]["file"] == ("elarax-command.webm", b"browser webm bytes", "audio/webm")
    assert call["data"]["model"] == "whisper-large-v3"
    assert "Preserve imperative verbs" in call["data"]["prompt"]
    assert "email addresses" in call["data"]["prompt"]
    assert call["data"]["response_format"] == "json"
    assert call["data"]["temperature"] == "0"
    assert call["timeout"] == 12
    assert service.last_error is None


def test_groq_transcription_prefers_standard_environment_key(monkeypatch) -> None:
    observed_authorization: list[str] = []

    def fake_post(url: str, **kwargs):
        observed_authorization.append(kwargs["headers"]["Authorization"])
        return FakeResponse(200, {"text": "check my calendar"})

    monkeypatch.setenv("GROQ_API_KEY", "standard-key")
    monkeypatch.setenv("AETHERBOT_GROQ_API_KEY", "legacy-alias-key")
    service = GroqTranscriptionService(
        enabled=True,
        request_post=fake_post,
    )

    assert service.transcribe_audio(b"audio", "audio/webm") == "check my calendar"
    assert observed_authorization == ["Bearer standard-key"]


def test_groq_transcription_maps_errors_without_response_or_key_details(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "never-expose-this-key")
    service = GroqTranscriptionService(
        enabled=True,
        request_post=lambda *args, **kwargs: FakeResponse(
            429,
            {"error": {"message": "quota for never-expose-this-key and private provider details"}},
        ),
    )

    assert service.transcribe_audio(b"audio", "audio/webm") is None
    assert service.last_error == "GroqUnavailable: rate limited"
    assert "never-expose" not in service.last_error
    assert "private provider" not in service.last_error


def test_local_whisper_writes_matching_suffix_and_cleans_up(monkeypatch, tmp_path) -> None:
    service = LocalWhisperTranscriptionService(
        cache_dir=tmp_path,
        enabled=True,
        allow_download=True,
        language="en",
    )
    observed_path: Path | None = None
    observed_options: dict | None = None

    class FakeModel:
        def transcribe(self, path: str, **options):
            nonlocal observed_path, observed_options
            observed_path = Path(path)
            observed_options = options
            assert observed_path.is_file()
            assert observed_path.read_bytes() == b"browser webm bytes"
            return {"text": " Send an email to Alice at example.com saying hello "}

    monkeypatch.setattr(service, "_availability_error", lambda: None)
    monkeypatch.setattr(service, "_load_model", lambda: FakeModel())

    transcript = service.transcribe_audio(b"browser webm bytes", "audio/webm")

    assert transcript == "Send an email to Alice at example.com saying hello"
    assert observed_path is not None and observed_path.suffix == ".webm"
    assert not observed_path.exists()
    assert observed_options is not None
    assert observed_options["language"] == "en"
    assert observed_options["fp16"] is False
    assert observed_options["temperature"] == 0
    assert "imperative verbs" in observed_options["initial_prompt"]
    assert service.last_error is None


def test_local_whisper_model_loads_once_and_only_on_request(monkeypatch, tmp_path) -> None:
    service = LocalWhisperTranscriptionService(
        cache_dir=tmp_path,
        enabled=True,
        allow_download=True,
    )
    loaded: list[tuple[str, str, str]] = []
    fake_model = object()

    fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    fake_whisper = SimpleNamespace(
        load_model=lambda model_name, *, device, download_root: (
            loaded.append((model_name, device, download_root)) or fake_model
        )
    )
    monkeypatch.setitem(__import__("sys").modules, "torch", fake_torch)
    monkeypatch.setitem(__import__("sys").modules, "whisper", fake_whisper)

    assert service._model is None
    assert service._load_model() is fake_model
    assert service._load_model() is fake_model
    assert loaded == [("base", "cpu", str(tmp_path))]


def test_provider_order_prefers_groq() -> None:
    groq = FakeProvider("groq transcript")
    local = FakeProvider("local transcript")
    gemini = FakeProvider("gemini transcript")
    service = VoiceTranscriptionService(  # type: ignore[arg-type]
        groq_provider=groq,
        cloud_provider=gemini,
        local_provider=local,
    )

    assert service.transcribe_audio(b"audio", "audio/webm") == "groq transcript"
    assert len(groq.calls) == 1
    assert gemini.calls == []
    assert local.calls == []
    assert service.last_provider == "groq"


def test_provider_order_falls_back_to_gemini() -> None:
    groq = FakeProvider(None, "GroqUnavailable: rate limited")
    local = FakeProvider("local transcript")
    gemini = FakeProvider("gemini transcript")
    service = VoiceTranscriptionService(  # type: ignore[arg-type]
        groq_provider=groq,
        cloud_provider=gemini,
        local_provider=local,
    )

    assert service.transcribe_audio(b"audio", "audio/webm") == "gemini transcript"
    assert len(groq.calls) == 1
    assert len(gemini.calls) == 1
    assert local.calls == []
    assert service.last_provider == "gemini"
    assert service.last_error is None


def test_provider_order_uses_local_whisper_last() -> None:
    groq = FakeProvider(None, configured=False)
    gemini = FakeProvider(None, "TranscriptionUnavailable: quota exhausted")
    local = FakeProvider("local transcript")
    service = VoiceTranscriptionService(  # type: ignore[arg-type]
        groq_provider=groq,
        cloud_provider=gemini,
        local_provider=local,
    )

    assert service.transcribe_audio(b"audio", "audio/webm") == "local transcript"
    assert groq.calls == []
    assert len(gemini.calls) == 1
    assert len(local.calls) == 1
    assert service.last_provider == "local-whisper"


def test_provider_order_preserves_unavailable_error_details() -> None:
    groq = FakeProvider(None, "GroqUnavailable: authentication rejected")
    gemini = FakeProvider(None, "TranscriptionUnavailable: quota exhausted")
    local = FakeProvider(None, "WhisperUnavailable: ffmpeg missing")
    service = VoiceTranscriptionService(  # type: ignore[arg-type]
        groq_provider=groq,
        cloud_provider=gemini,
        local_provider=local,
    )

    assert service.transcribe_audio(b"audio", "audio/webm") is None
    assert service.last_error is not None
    assert service.last_error.startswith("TranscriptionUnavailable:")
    assert "authentication rejected" in service.last_error
    assert "ffmpeg missing" in service.last_error
    assert "quota exhausted" in service.last_error
