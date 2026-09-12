"""Runtime paths and local configuration for ElaraX."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# The documented configuration file is the project-root `.env`. Also accept
# the backend-local names used by older local setups so a restart does not
# silently disable configured providers.
for env_file in (
    PROJECT_ROOT / ".env",
    PROJECT_ROOT / "backend" / ".env",
    PROJECT_ROOT / "backend" / ".env.txt",
):
    load_dotenv(env_file, override=False)

SECRETS_DIR = Path(os.getenv("AETHERBOT_SECRETS_DIR", PROJECT_ROOT / "secrets"))
DATA_DIR = Path(os.getenv("AETHERBOT_DATA_DIR", PROJECT_ROOT / "data"))
AUTH_DATABASE_FILE = Path(os.getenv("ELARAX_AUTH_DATABASE_FILE", DATA_DIR / "elarax.sqlite3"))
AUTH_USERS_FILE = Path(os.getenv("ELARAX_AUTH_USERS_FILE", DATA_DIR / "users.json"))
AUTH_SESSIONS_FILE = Path(os.getenv("ELARAX_AUTH_SESSIONS_FILE", DATA_DIR / "auth_sessions.json"))
INVOICE_AUTOMATION_SETTINGS_FILE = Path(
    os.getenv("AETHERBOT_INVOICE_AUTOMATION_SETTINGS_FILE", DATA_DIR / "invoice_automation.json")
)
ACTION_ITEMS_FILE = Path(
    os.getenv("AETHERBOT_ACTION_ITEMS_FILE", DATA_DIR / "action_items.json")
)
INVOICE_AUTOMATION_INTERVAL_SECONDS = int(
    os.getenv("AETHERBOT_INVOICE_AUTOMATION_INTERVAL_SECONDS", "300")
)
INVOICE_AUTOMATION_MAX_REPLIES_PER_RUN = int(
    os.getenv("AETHERBOT_INVOICE_AUTOMATION_MAX_REPLIES_PER_RUN", "3")
)

GOOGLE_CLIENT_FILE = Path(
    os.getenv("AETHERBOT_GOOGLE_CLIENT_FILE", SECRETS_DIR / "google_oauth_client.json")
)
GOOGLE_TOKEN_FILE = Path(os.getenv("AETHERBOT_GOOGLE_TOKEN_FILE", DATA_DIR / "google_token.enc"))
TOKEN_ENCRYPTION_KEY_FILE = Path(
    os.getenv("AETHERBOT_TOKEN_KEY_FILE", SECRETS_DIR / "token_encryption.key")
)
GOOGLE_REDIRECT_URI = os.getenv(
    "AETHERBOT_GOOGLE_REDIRECT_URI",
    "http://localhost:8000/api/v1/auth/google/callback",
)
FRONTEND_ORIGIN = os.getenv("AETHERBOT_FRONTEND_ORIGIN", "http://localhost:3000")
AETHERBOT_TIMEZONE = os.getenv("AETHERBOT_TIMEZONE", "Asia/Kolkata")

# Provider-neutral LLM settings. Existing Gemini variables remain supported;
# setting LLM_PROVIDER=openai (or another OpenAI-compatible provider) lets
# optional services use the same business logic with a different endpoint.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().casefold() or "gemini"
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
if not LLM_MODEL:
    LLM_MODEL = "gpt-4o-mini"

# OpenRouter is an OpenAI-compatible research/synthesis provider. Keep its
# dedicated variables so it can be used even while Gemini remains the default
# assistant/voice provider.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
OPENROUTER_MODEL_QUALITY = os.getenv(
    "OPENROUTER_MODEL_QUALITY", "meta-llama/llama-3.1-8b-instruct"
).strip()
OPENROUTER_MODEL_FAST = os.getenv(
    "OPENROUTER_MODEL_FAST", OPENROUTER_MODEL_QUALITY
).strip()
OPENROUTER_TIMEOUT_SECONDS = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "20"))
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
TAVILY_TIMEOUT_SECONDS = float(os.getenv("TAVILY_TIMEOUT_SECONDS", "15"))
# Reserved optional adapter variables for deployments that provide a Wili
# search endpoint. No endpoint is assumed when these are absent.
WILI_API_KEY = os.getenv("WILI_API_KEY", "").strip()
WILI_BASE_URL = os.getenv("WILI_BASE_URL", "").strip().rstrip("/")
GEMINI_API_KEY_FILE = Path(
    os.getenv("AETHERBOT_GEMINI_API_KEY_FILE", SECRETS_DIR / "gemini_api_key.txt")
)
GEMINI_MODEL = os.getenv("AETHERBOT_GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_TRANSCRIPTION_MODEL = os.getenv(
    "AETHERBOT_GEMINI_TRANSCRIPTION_MODEL",
    "gemini-3.5-flash",
)
GEMINI_TTS_MODEL = os.getenv("AETHERBOT_GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
GEMINI_TTS_VOICE = os.getenv("AETHERBOT_GEMINI_TTS_VOICE", "Kore")
GEMINI_TIMEOUT_MS = int(os.getenv("AETHERBOT_GEMINI_TIMEOUT_MS", "30000"))
GEMINI_EMAIL_SIGNALS_TIMEOUT_MS = int(
    os.getenv("AETHERBOT_GEMINI_EMAIL_SIGNALS_TIMEOUT_MS", "5000")
)
GROQ_TRANSCRIPTION_MODEL = (
    os.getenv("GROQ_TRANSCRIPTION_MODEL", "whisper-large-v3").strip()
    or "whisper-large-v3"
)
GROQ_TRANSCRIPTION_TIMEOUT_SECONDS = int(
    os.getenv("GROQ_TRANSCRIPTION_TIMEOUT_SECONDS", "20")
)
WHISPER_MODEL = os.getenv("AETHERBOT_WHISPER_MODEL", "base").strip() or "base"
WHISPER_CACHE_DIR = Path(
    os.getenv("AETHERBOT_WHISPER_CACHE_DIR", Path.home() / ".cache" / "whisper")
)
WHISPER_LANGUAGE = os.getenv("AETHERBOT_WHISPER_LANGUAGE", "").strip() or None
WHISPER_ALLOW_DOWNLOAD = os.getenv("AETHERBOT_WHISPER_ALLOW_DOWNLOAD", "").strip().casefold() in {
    "1",
    "true",
    "yes",
    "on",
}
