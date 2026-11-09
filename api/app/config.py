"""Settings read from environment variables (12-factor). `.env.example` documents each one."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-secret-change-me-0123456789abcdef"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://swr:swr@localhost:5432/swr"
    redis_url: str = "redis://localhost:6379/0"

    # Shared with Next.js: it signs the API token, FastAPI verifies it (ADR-017).
    api_jwt_secret: str = Field(default=DEV_JWT_SECRET, min_length=32)
    api_jwt_audience: str = "swr-api"
    api_jwt_issuer: str = "swr-web"

    cors_origins: str = "http://localhost:3000"

    # Manual refresh rate limit (per user, per league).
    refresh_min_interval_seconds: int = 60

    @model_validator(mode="after")
    def _no_dev_secret_in_production(self) -> "Settings":
        if self.environment == "production" and self.api_jwt_secret == DEV_JWT_SECRET:
            raise ValueError("API_JWT_SECRET must be set to a real secret in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
