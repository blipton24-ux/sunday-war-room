"""`sync_runs` bookkeeping shared by the API (creates a run when it enqueues) and the worker
(marks it running / done / failed). The UI reads job status from here, not from Redis, so
status survives Redis restarts and is scoped to the user who asked."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from arq import Retry
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.base import AdapterError, AdapterSchemaError, NotFoundOnPlatform
from app.db.models import SyncRun
from app.logging import get_logger

log = get_logger("jobs")


def new_job_id() -> str:
    return uuid.uuid4().hex


async def create_run(
    db: AsyncSession,
    kind: str,
    *,
    league_id: int | None = None,
    requested_by: int | None = None,
    job_id: str | None = None,
) -> SyncRun:
    run = SyncRun(
        kind=kind,
        job_id=job_id or new_job_id(),
        league_id=league_id,
        requested_by=requested_by,
        status="queued",
    )
    db.add(run)
    await db.commit()
    return run


MAX_TRIES = 3


def is_transient(exc: BaseException) -> bool:
    """Worth retrying: the platform was down or slow. Not: bad input or a changed format."""
    return isinstance(exc, AdapterError) and not isinstance(
        exc, AdapterSchemaError | NotFoundOnPlatform
    )


async def run_tracked(
    sessionmaker: async_sessionmaker[AsyncSession],
    run_id: int,
    body: Callable[[AsyncSession], Awaitable[dict[str, Any] | None]],
    *,
    job_try: int = 1,
) -> dict[str, Any] | None:
    """Run a job body with its sync_run marked running -> done/failed.

    Transient failures go back to "queued" and ask ARQ to retry with backoff (15s, 30s);
    after MAX_TRIES, or for permanent errors, the run is marked failed.
    """
    async with sessionmaker() as db:
        run = await db.get(SyncRun, run_id)
        if run is None:
            raise LookupError(f"sync_run {run_id} not found")
        structlog.contextvars.bind_contextvars(job_id=run.job_id, kind=run.kind)
        run.status, run.started_at, run.error = "running", datetime.now(UTC), None
        await db.commit()

    try:
        async with sessionmaker() as db:
            result = await body(db)
    except Exception as exc:
        retry = is_transient(exc) and job_try < MAX_TRIES
        async with sessionmaker() as db:
            run = await db.get(SyncRun, run_id)
            assert run is not None
            run.status = "queued" if retry else "failed"
            run.finished_at = None if retry else datetime.now(UTC)
            run.error = f"{type(exc).__name__}: {exc}"[:2000]
            await db.commit()
        if retry:
            log.warning("job_retry", run_id=run_id, job_try=job_try, error=str(exc))
            raise Retry(defer=15 * job_try) from exc
        log.exception("job_failed", run_id=run_id)
        raise

    async with sessionmaker() as db:
        run = await db.get(SyncRun, run_id)
        assert run is not None
        run.status, run.finished_at, run.result = "done", datetime.now(UTC), result
        await db.commit()
    log.info("job_done", run_id=run_id)
    return result
