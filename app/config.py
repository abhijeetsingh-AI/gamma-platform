# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # ── Gemini LLM ──────────────────────────────
    gemini_api_key: str  = Field(..., env="GEMINI_API_KEY")
    gemini_model: str    = "gemini-1.5-pro"

    # ── Deepgram STT ─────────────────────────────
    deepgram_api_key: str = Field(..., env="DEEPGRAM_API_KEY")
    deepgram_model: str   = "nova-2-phonecall"

    # ── Google Cloud TTS (optional until GCP creds added) ──
    google_credentials_path: str = Field(default="", env="GOOGLE_APPLICATION_CREDENTIALS")
    tts_language_code: str  = "en-US"
    tts_voice_female: str   = "en-US-Neural2-F"
    tts_voice_male: str     = "en-US-Neural2-D"

    # ── Twilio ───────────────────────────────────
    twilio_account_sid: str  = Field(..., env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str   = Field(..., env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str = Field(..., env="TWILIO_PHONE_NUMBER")
    twilio_webhook_url: str  = Field(..., env="TWILIO_WEBHOOK_URL")

    # ── App ──────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./gamma.db"
    secret_key: str   = Field(..., env="SECRET_KEY")
    redis_url: str    = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    upload_dir: str   = "./uploads"
    base_url: str     = Field(..., env="BASE_URL")

    # ── TTS mode ─────────────────────────────────
    # "twilio" = use Twilio <Say> (no GCP needed)
    # "google" = use Google Neural2 (requires GCP creds)
    tts_provider: str = Field(default="twilio", env="TTS_PROVIDER")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
