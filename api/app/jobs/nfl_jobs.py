"""ARQ jobs for shared NFL data (nflverse)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.config import get_settings
from app.db.models import PlayerWeekStats
from app.jobs.tracking import create_run, run_tracked
from app.services.grading import grade_finished
from app.services.ingest import ingest_nflverse
from app.sources.nflverse import current_season

Ctx = dict[str, Any]


def seasons_to_load(current: int) -> list[int]:
    """Every season from NFLVERSE_FIRST_SEASON through the current one."""
    return list(range(get_settings().nflverse_first_season, current + 1))


async def ingest_nflverse_job(ctx: Ctx, run_id: int | None = None, full: bool = False) -> Any:
    """Reload nflverse data. Default: only the current season (fast, runs daily);
    `full=True` reloads every season (first deploy, or after a model/data fix)."""
    sm = ctx["sessionmaker"]
    if run_id is None:
        async with sm() as db:
            run_id = (await create_run(db, "ingest_nflverse")).id
    current = current_season()
    seasons = seasons_to_load(current) if full else [current]

    async def body(db: Any) -> dict[str, Any]:
        loaded = await ingest_nflverse(db, seasons)
        graded = await grade_finished(db, current)
        return {"seasons": seasons, **loaded, "graded": graded}

    return await run_tracked(sm, run_id, body, job_try=ctx.get("job_try", 1))


INITIAL_INGEST_JOB_ID = "initial-nflverse-ingest"


async def enqueue_initial_ingest(ctx: Ctx) -> bool:
    """On worker start: if the database holds no NFL stats at all (a brand-new deploy), start
    a full nflverse load now instead of waiting for tomorrow's scheduled one. Without history,
    projections fall back to generic values. Returns True when a load was queued.
    """
    async with ctx["sessionmaker"]() as db:
        has_stats = await db.scalar(select(PlayerWeekStats.gsis_id).limit(1))
    if has_stats is not None:
        return False
    # Fixed job id: several workers starting together queue it once.
    await ctx["redis"].enqueue_job("ingest_nflverse_job", None, True, _job_id=INITIAL_INGEST_JOB_ID)
    return True
