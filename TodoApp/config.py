from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "FastAPI Boilerplate"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    # Override in .env with a PostgreSQL URL for production:
    # DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
    DATABASE_URL: str = "sqlite:///./todosapp.db"

    # ── JWT ──────────────────────────────────────────────────────────────────
    # Generate a strong key: openssl rand -hex 32
    SECRET_KEY: str = "change-me-in-production-generate-with-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 20

    # ── Rate limiting (requests per minute, per IP) ───────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
