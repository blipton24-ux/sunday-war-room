"""Database- and Redis-backed edge cases found by the step 14 coverage run."""

import importlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import League, Matchup, Player, SyncRun
from app.jobs import nfl_jobs
from app.jobs.league_jobs import sync_league_job
from app.jobs.tracking import create_run, run_tracked
from app.services import ingest
from app.services.projections import compute_projections
from app.services.sync import _player_ids, players_are_stale, sync_league, upsert_platform_players
from tests.integration.test_ingest import frames
from tests.sleeper_fixtures import LEAGUE_ID

pytestmark = pytest.mark.integration


class RecordingRedis:
    def __init__(self) -> None:
        self.jobs: list[tuple[Any, ...]] = []

    async def enqueue_job(self, *args: Any, **kwargs: Any) -> None:
        self.jobs.append(args)


# --------------------------------------------------------------------------- plumbing
async def test_request_sessions_reach_the_database(engine: Any) -> None:
    from app.db.session import get_db

    async for session in get_db():
        assert (await session.execute(text("select 1"))).scalar() == 1


async def test_the_queue_connects_to_redis_and_closes_cleanly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import queue

    base = get_settings().redis_url.rsplit("/", 1)[0]
    monkeypatch.setattr(queue, "get_settings", lambda: Settings(redis_url=f"{base}/15"))
    pool = await queue.get_queue()
    assert await pool.ping()  # type: ignore[attr-defined]
    assert await queue.get_queue() is pool  # one shared connection
    await queue.close_queue()
    assert queue._pool is None


# --------------------------------------------------------------------------- the worker
def test_worker_registers_every_job_and_its_schedule() -> None:
    from app.worker import WorkerSettings

    assert {f.__name__ for f in WorkerSettings.functions} == {  # type: ignore[attr-defined]
        "connect_sleeper",
        "sync_league_job",
        "sync_players_job",
        "ingest_nflverse_job",
    }
    assert {c.name for c in WorkerSettings.cron_jobs} == {
        "cron:sync_all_leagues",
        "cron:sync_players_job",
        "cron:ingest_nflverse_job",
    }
    assert WorkerSettings.max_tries == 3


async def test_worker_start_prepares_its_context_and_queues_the_first_load(
    db: AsyncSession,
) -> None:
    from app import worker

    redis = RecordingRedis()
    ctx: dict[str, Any] = {"redis": redis}
    await worker.startup(ctx)
    try:
        assert "sleeper" in ctx["adapters"] and "sessionmaker" in ctx
        assert [job[0] for job in redis.jobs] == ["ingest_nflverse_job"]  # empty database
    finally:
        await worker.shutdown(ctx)


async def test_first_run_load_and_schedule_can_be_switched_off(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end tests turn these off so their seeded data is never replaced."""
    monkeypatch.setattr(nfl_jobs, "get_settings", lambda: Settings(initial_ingest=False))
    ctx: dict[str, Any] = {"redis": RecordingRedis(), "sessionmaker": None}
    assert await nfl_jobs.enqueue_initial_ingest(ctx) is False
    assert ctx["redis"].jobs == []

    import app.worker as worker_module

    monkeypatch.setenv("CRON_ENABLED", "false")
    get_settings.cache_clear()
    try:
        assert importlib.reload(worker_module).WorkerSettings.cron_jobs == []
    finally:
        monkeypatch.delenv("CRON_ENABLED")
        get_settings.cache_clear()
        importlib.reload(worker_module)


# --------------------------------------------------------------------------- jobs
async def test_nflverse_job_loads_grades_and_records_its_run(
    db: AsyncSession, ctx: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[int]] = []

    def fake_fetch(seasons: list[int]) -> Any:
        seen.append(list(seasons))
        return frames()

    monkeypatch.setattr(nfl_jobs, "current_season", lambda: 2026)
    monkeypatch.setattr(ingest, "fetch_frames", fake_fetch)

    result = await nfl_jobs.ingest_nflverse_job(ctx)  # no run id: the job creates its own
    assert seen == [[2026]]  # daily run: the current season only
    assert result["games"] == 1 and result["player_weeks"] == 2 and result["graded"] == 0
    run = await db.scalar(select(SyncRun).where(SyncRun.kind == "ingest_nflverse"))
    assert run is not None and run.status == "done"

    await nfl_jobs.ingest_nflverse_job(ctx, None, True)  # the first-run load: every season
    assert seen[-1] == [2022, 2023, 2024, 2025, 2026]
    assert nfl_jobs.seasons_to_load(2024) == [2022, 2023, 2024]


async def test_syncing_a_league_that_does_not_exist_fails_without_retrying(
    db: AsyncSession, ctx: dict[str, Any]
) -> None:
    run = await create_run(db, "sync_league")
    with pytest.raises(LookupError, match="league 999 not found"):
        await sync_league_job(ctx, run.id, 999)
    await db.refresh(run)
    assert run.status == "failed" and "LookupError" in (run.error or "")


async def test_a_past_seasons_league_is_synced_through_its_final_week(
    db: AsyncSession, ctx: dict[str, Any]
) -> None:
    stub = League(platform="sleeper", external_id=LEAGUE_ID, season=2025, name="last year")
    db.add(stub)
    await db.commit()
    run = await create_run(db, "sync_league", league_id=stub.id)
    result = await sync_league_job(ctx, run.id, stub.id)
    assert result["week"] == 17  # the NFL says it is 2026, so a 2025 league is over


async def test_a_job_for_a_missing_run_record_is_an_error(ctx: dict[str, Any]) -> None:
    async def body(_db: AsyncSession) -> None:
        return None

    with pytest.raises(LookupError, match="sync_run 424242 not found"):
        await run_tracked(ctx["sessionmaker"], 424242, body)


# --------------------------------------------------------------------------- services
async def test_player_list_staleness(db: AsyncSession, ctx: dict[str, Any]) -> None:
    assert await players_are_stale(db) is True  # no players at all
    await upsert_platform_players(db, "sleeper", await ctx["adapters"]["sleeper"].fetch_players())
    assert await players_are_stale(db) is False  # just refreshed
    old = datetime.now(UTC) - timedelta(days=2)
    await db.execute(update(Player).values(updated_at=old))
    await db.commit()
    assert await players_are_stale(db) is True
    assert await _player_ids(db, set()) == {}  # nothing asked, nothing queried


async def test_teams_with_no_opponent_are_stored_as_byes(
    db: AsyncSession, ctx: dict[str, Any]
) -> None:
    adapter = ctx["adapters"]["sleeper"]
    await upsert_platform_players(db, "sleeper", await adapter.fetch_players())
    real = adapter.fetch_matchups

    async def one_pair_without_opponents(league: Any, week: int) -> Any:
        rows = await real(league, week)
        dropped = rows[-1].matchup_key  # one complete pairing loses its opponent link
        return [replace(r, matchup_key=None) if r.matchup_key == dropped else r for r in rows]

    adapter.fetch_matchups = one_pair_without_opponents
    await sync_league(db, adapter, LEAGUE_ID, current_week=9)
    no_opponent = await db.scalar(
        select(func.count()).select_from(Matchup).where(Matchup.away_team_id.is_(None))
    )
    assert no_opponent == 2


async def test_a_league_with_no_rosters_has_nothing_to_project(db: AsyncSession) -> None:
    empty = League(platform="sleeper", external_id="1", season=2026, name="empty", scoring_rules={})
    db.add(empty)
    await db.commit()
    assert await compute_projections(db, empty, 9) == {"computed": 0, "frozen": 0}
