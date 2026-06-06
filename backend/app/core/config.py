"""
growders.core.config
────────────────────
Single source of truth for all runtime configuration.
Uses pydantic-settings so every value is typed, validated,
and can be overridden by environment variables or a .env file.

Swap any external service by changing one env var — no code changes needed.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_secret_key: str = Field(min_length=32)
    app_debug: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = ""          # empty → SQLite fallback
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            url = self.database_url
            # Railway injects postgresql:// — SQLAlchemy async needs postgresql+asyncpg://
            if url.startswith("postgresql://") or url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return "sqlite+aiosqlite:///./data/growders.db"

    # ── Cache ─────────────────────────────────────────────────────────────
    redis_url: str = ""             # empty → in-memory cache
    cache_ttl_seconds: int = 300

    @property
    def cache_backend(self) -> Literal["memory", "redis"]:
        return "redis" if self.redis_url else "memory"

    # ── LLM ──────────────────────────────────────────────────────────────
    llm_provider: Literal["mock", "groq", "openai", "gemini"] = "mock"
    groq_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_model: str = ""
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.3

    # ── WhatsApp ─────────────────────────────────────────────────────────
    whatsapp_provider: Literal["mock", "360dialog", "vonage"] = "mock"
    whatsapp_api_key: str = ""
    whatsapp_api_url: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = "change-me"

    # ── Email ─────────────────────────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from_name: str = "Growders"

    # ── Google Calendar ───────────────────────────────────────────────────
    google_calendar_credentials_json: str = ""
    google_calendar_id: str = ""

    # ── Security ──────────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allowed_hosts: str = "localhost,127.0.0.1"
    rate_limit_per_minute: int = 60
    rate_limit_chat_per_minute: int = 20

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # Railway auto-injects RAILWAY_PUBLIC_DOMAIN (e.g. growders-mvp-production.up.railway.app).
    # We include it in trusted_hosts so TrustedHostMiddleware never blocks its own hostname.
    railway_public_domain: str = ""

    @property
    def trusted_hosts(self) -> list[str]:
        hosts = [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]
        if self.railway_public_domain:
            host = self.railway_public_domain.strip()
            if host and host not in hosts:
                hosts.append(host)
        return hosts

    # ── Async / Workers ───────────────────────────────────────────────────
    task_backend: Literal["fastapi", "celery"] = "fastapi"
    celery_broker_url: str = ""

    # ── Observability ─────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    sentry_dsn: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.
    Call get_settings() everywhere — never instantiate Settings() directly.
    """
    return Settings()
