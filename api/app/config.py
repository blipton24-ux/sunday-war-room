"""Settings read from environment variables (12-factor). `.env.example` documents each one."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://swr:swr@localhost:5432/swr"
    redis_url: str = "redis://localhost:6379/0"

    # Shared with Next.js: it signs the API token, FastAPI verifies it (ADR-017).
    api_jwt_secret: str = Field(default="change-me", min_length=8)
    api_jwt_audience: str = "swr-api"
    api_jwt_issuer: str = "swr-web"

    cors_origins: str = "http://localhost:3000"

    # Manual refresh rate limit (per user, per league).
    refresh_min_interval_seconds: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
