"""ARQ worker: the second mode of the api/ codebase (ADR-013, ADR-016).

Run with:  arq app.worker.WorkerSettings
"""

from __future__ import annotations

from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings
from arq.typing import WorkerCoroutine

from app.adapters.sleeper import SleeperAdapter
from app.config import get_settings
from app.db.session import get_engine, get_sessionmaker
from app.jobs.league_jobs import (
    connect_sleeper,
    live_update_job,
    sync_all_leagues,
    sync_league_job,
    sync_players_job,
)
from app.jobs.nfl_jobs import enqueue_initial_ingest, ingest_nflverse_job
from app.jobs.tracking import MAX_TRIES
from app.logging import configure_logging, get_logger

settings = get_settings()
log = get_logger("worker")


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging(settings.log_level, json=settings.environment != "development")
    ctx["sessionmaker"] = get_sessionmaker()
    ctx["adapters"] = {"sleeper": SleeperAdapter()}
    if await enqueue_initial_ingest(ctx):
        log.info("initial_nflverse_ingest_queued")
    log.info("worker_started")


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["adapters"]["sleeper"].aclose()
    await get_engine().dispose()


class WorkerSettings:
    functions: ClassVar[list[WorkerCoroutine]] = [
        connect_sleeper,
        live_update_job,
        sync_league_job,
        sync_players_job,
        ingest_nflverse_job,
    ]
    cron_jobs: ClassVar[list[Any]] = [] if not settings.cron_enabled else [
        cron(sync_all_leagues, minute=5, run_at_startup=False),  # hourly, at :05
        # Every minute; returns at once unless an NFL game is about to start or is live.
        cron(live_update_job, unique=True, timeout=50),
        cron(sync_players_job, hour=9, minute=15),  # daily (UTC)
        # Daily: nflverse publishes stats overnight after games (Tuesday run catches MNF).
        cron(ingest_nflverse_job, hour={10}, minute=0),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_tries = MAX_TRIES  # transient failures retry with backoff (app/jobs/tracking.py)
    job_timeout = 600
    keep_result = 3600
