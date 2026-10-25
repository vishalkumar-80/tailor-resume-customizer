from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables / backend/.env."""

    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parent.parent / ".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-3.5-flash-lite"
    # "low" keeps Gemini 3.x thinking models fast; set empty to disable thinkingConfig.
    gemini_thinking_level: str = "low"
    gemini_timeout_seconds: float = 60.0

    # Comma-separated list of origins allowed to call the API (the Next.js app).
    allowed_origins: str = "http://localhost:3000"

    max_upload_mb: float = 4.0  # Vercel functions cap request bodies at 4.5 MB
    max_jd_chars: int = 15_000
    min_jd_chars: int = 100
    max_resume_chars: int = 30_000
    max_pdf_pages: int = 10

    # Simple per-IP limiter for the LLM endpoints.
    rate_limit_per_minute: int = Field(default=8, ge=1)
    export_rate_limit_per_minute: int = Field(default=30, ge=1)
    max_json_body_kb: int = 256
    # Header carrying the real client IP behind a trusted proxy (set "x-real-ip" on Vercel). Empty = socket peer.
    client_ip_header: str = ""
    enable_docs: bool = False

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)


@lru_cache
def get_settings() -> Settings:
    return Settings()
