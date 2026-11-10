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

    # First season loaded from nflverse for the model's history and backtests.
    nflverse_first_season: int = 2022

    # Where Sleeper's public API lives. Overridden only by end-to-end tests (a local stand-in
    # serving recorded responses), so tests never depend on the live service.
    sleeper_base_url: str = "https://api.sleeper.app/v1"
    # ESPN's public NFL scoreboard: game clocks for live win chance (ADR-044). Same override.
    espn_scoreboard_url: str = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

    # Background work switches. Both default on; end-to-end tests turn them off so the data they
    # seed is never replaced by a scheduled or first-run load from the internet.
    initial_ingest: bool = True  # the worker loads NFL history on first start
    cron_enabled: bool = True  # hourly syncs and the daily player/nflverse refresh

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
