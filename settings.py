"""
Centralized configuration for CircuitMind.

All environment-specific values and previously-hardcoded config live here.
Everything is read once from `.env` (or real environment variables) via
pydantic-settings, and imported wherever it's needed instead of scattering
os.environ.get() calls through the codebase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Secrets / deployment-specific ───────────────────────────
    groq_api_key: str | None = None
    circuitmind_api_key: str | None = None
    rate_limit_redis_url: str | None = None

    allowed_origins: str = (
        "http://localhost:8501,http://127.0.0.1:8501,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    # ── LangChain (optional tracing) ────────────────
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "circuitmind"

    # ── App metadata ─────────────────────────────────────────────
    app_title: str = "CircuitMind API"
    app_description: str = "AI-powered circuit generator, explainer, and diagnostics tool"
    app_version: str = "1.0.0"

    # ── Logging ──────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: str = "%(asctime)s [%(levelname)s] %(message)s"

    # ── Rate limit ───────────────────────────────────────────────
    # Single gateway endpoint now, so a single rate limit replaces the old
    # per-route ones (generate/explain/diagnose/export/hint/generate-and-explain).
    chat_rate_limit: str = "10/minute"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
