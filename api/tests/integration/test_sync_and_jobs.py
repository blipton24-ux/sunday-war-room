"""League sync into Postgres, the job wrappers, and one real Redis + ARQ worker run."""

from typing import Any

import pytest
from arq import Retry
from arq.connections import RedisSettings, create_pool
from arq.worker import Worker
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import (
    League,
    LeagueMembership,
    LeagueTransaction,
    Matchup,
    PlatformAccount,
    Player,
    PlayerWeekStats,
    RosterEntry,
    SyncRun,
    Team,
)
from app.jobs.league_jobs import connect_sleeper, sync_all_leagues, sync_league_job
from app.jobs.tracking import create_run
from app.services.sync import sync_league, upsert_platform_players
from tests.conftest import make_user
from tests.sleeper_fixtures import LEAGUE_ID, fx

pytestmark = pytest.mark.integration


async def count(db: AsyncSession, model: Any, *where: Any) -> int:
    return int(await db.scalar(select(func.count()).select_from(model).where(*where)) or 0)


# --------------------------------------------------------------------------- service
async def test_sync_league_writes_everything_and_is_idempotent(
    db: AsyncSession, ctx: dict[str, Any]
) -> None:
    adapter = ctx["adapters"]["sleeper"]
    await upsert_platform_players(db, "sleeper", await adapter.fetch_players())

    for _ in range(2):  # second run must converge on the same rows
        league = await sync_league(db, adapter, LEAGUE_ID, current_week=9, history_weeks=[8])

    assert league.name == "Fixture League"
    assert league.scoring_rules["rec"] == 0.5
    assert league.current_week == 9 and league.last_synced_at is not None
    assert await count(db, Team, Team.league_id == league.id) == 12
    assert await count(db, Matchup, Matchup.week == 8) == 6
    assert await count(db, Matchup, Matchup.week == 9) == 6

    week8 = (await db.scalars(select(Matchup).where(Matchup.week == 8))).all()
    assert all(m.home_score and m.away_score for m in week8)

    total_rostered = sum(len(r["players"] or []) for r in fx("rosters"))
    assert await count(db, RosterEntry, RosterEntry.week == 9) == total_rostered
    starters_w8 = await count(db, RosterEntry, RosterEntry.week == 8, RosterEntry.is_starter)
    assert 0 < starters_w8 <= 12 * 9


# --------------------------------------------------------------------------- jobs
async def test_sync_stores_league_rules_waiver_order_and_transactions(
    db: AsyncSession, ctx: dict[str, Any]
) -> None:
    """P2 (ADR-046): what waivers and trades need, stored on every sync, idempotently."""
    adapter = ctx["adapters"]["sleeper"]
    await upsert_platform_players(db, "sleeper", await adapter.fetch_players())
    for _ in range(2):
        league = await sync_league(db, adapter, LEAGUE_ID, current_week=9, history_weeks=[8])

    assert league.waiver_rules["kind"] == "faab" and league.waiver_rules["budget"] == 100
    assert league.season_rules["kind"] == "dynasty"
    assert league.season_rules["playoff_week_start"] == 15

    teams = (await db.scalars(select(Team).where(Team.league_id == league.id))).all()
    assert sorted(t.waiver_position for t in teams if t.waiver_position) == list(range(1, 13))

    txs = (
        await db.scalars(
            select(LeagueTransaction)
            .where(LeagueTransaction.league_id == league.id)
            .order_by(LeagueTransaction.created_at)
        )
    ).all()
    assert [(t.week, t.kind, t.status) for t in txs] == [
        (8, "waiver", "complete"),
        (8, "waiver", "failed"),
        (9, "trade", "complete"),
        (9, "free_agent", "complete"),
    ]
    assert txs[-1].drops == {"12457": "8"}


async def test_connect_job_links_account_and_lists_leagues(
    db: AsyncSession, ctx: dict[str, Any]
) -> None:
    user = await make_user(db, "ana@example.com")
    run = await create_run(db, "sleeper_connect", requested_by=user.id)

    result = await connect_sleeper(ctx, run.id, user.id, "fixtureuser")

    assert result["season"] == 2026
    assert [lg["external_id"] for lg in result["leagues"]] == [LEAGUE_ID]
    acct = await db.scalar(select(PlatformAccount).where(PlatformAccount.user_id == user.id))
    assert acct is not None and acct.display_name == "fixtureuser"
    await db.refresh(run)
    assert run.status == "done" and run.result == result


async def test_connect_job_unknown_user_fails_without_retry(
    db: AsyncSession, ctx: dict[str, Any]
) -> None:
    user = await make_user(db, "ana@example.com")
    run = await create_run(db, "sleeper_connect", requested_by=user.id)
    with pytest.raises(Exception, match="nobody"):
        await connect_sleeper(ctx, run.id, user.id, "nobody")
    await db.refresh(run)
    assert run.status == "failed" and "NotFoundOnPlatform" in (run.error or "")


async def test_sync_job_first_run_backfills_history(db: AsyncSession, ctx: dict[str, Any]) -> None:
    league = League(platform="sleeper", external_id=LEAGUE_ID, season=2026, name="stub")
    db.add(league)
    await db.commit()
    run = await create_run(db, "sync_league", league_id=league.id)

    result = await sync_league_job(ctx, run.id, league.id)

    assert result["league_id"] == league.id and result["week"] == 9
    # Every rostered player (313) plus the realistic free agents (P2 waivers) was projected.
    assert result["computed"] > 313
    assert result["rest_of_season"] == result["computed"]
    assert await count(db, Player) > 250  # players were stale (empty) so they were loaded
    # First sync back-fills weeks 1..8 plus the current week.
    weeks = (await db.scalars(select(Matchup.week).distinct())).all()
    assert sorted(weeks) == list(range(1, 10))
    await db.refresh(run)
    assert run.status == "done"


async def test_sync_job_transient_failure_requeues(db: AsyncSession, ctx: dict[str, Any]) -> None:
    league = League(platform="sleeper", external_id=LEAGUE_ID, season=2026, name="stub")
    db.add(league)
    await db.commit()
    run = await create_run(db, "sync_league", league_id=league.id)
    ctx["router"].get("/state/nfl").respond(503)

    with pytest.raises(Retry):
        await sync_league_job(ctx, run.id, league.id)
    await db.refresh(run)
    assert run.status == "queued" and "503" in (run.error or "")

    ctx["job_try"] = 3  # last attempt: now it is recorded as failed
    with pytest.raises(Exception, match="503"):
        await sync_league_job(ctx, run.id, league.id)
    await db.refresh(run)
    assert run.status == "failed"


async def test_hourly_cron_enqueues_each_followed_league_once(
    db: AsyncSession, ctx: dict[str, Any]
) -> None:
    user = await make_user(db, "ana@example.com")
    followed = League(platform="sleeper", external_id="1", season=2026, name="A")
    orphan = League(platform="sleeper", external_id="2", season=2026, name="nobody follows")
    db.add_all([followed, orphan])
    await db.flush()
    db.add(LeagueMembership(user_id=user.id, league_id=followed.id))
    await db.commit()

    enqueued: list[tuple[Any, ...]] = []

    class FakeRedis:
        async def enqueue_job(self, *args: Any, **kwargs: Any) -> None:
            enqueued.append(args)

    ctx["redis"] = FakeRedis()
    assert await sync_all_leagues(ctx) == 1
    assert await sync_all_leagues(ctx) == 0  # still queued: not enqueued twice
    assert [a[2] for a in enqueued] == [followed.id]


# --------------------------------------------------------------------------- real queue
async def test_real_redis_and_worker_run_a_sync(db: AsyncSession, ctx: dict[str, Any]) -> None:
    """End to end through Redis: enqueue like the API does, run an ARQ worker in burst mode."""
    league = League(platform="sleeper", external_id=LEAGUE_ID, season=2026, name="stub")
    db.add(league)
    await db.commit()
    run = await create_run(db, "sync_league", league_id=league.id)

    redis_settings = RedisSettings.from_dsn(get_settings().redis_url.rsplit("/", 1)[0] + "/15")
    pool = await create_pool(redis_settings)
    await pool.flushdb()
    try:
        await pool.enqueue_job("sync_league_job", run.id, league.id, _job_id=run.job_id)

        async def startup(worker_ctx: dict[str, Any]) -> None:
            worker_ctx.update(sessionmaker=ctx["sessionmaker"], adapters=ctx["adapters"])

        worker = Worker(
            functions=[sync_league_job],
            redis_pool=pool,
            burst=True,
            on_startup=startup,  # type: ignore[arg-type]
            handle_signals=False,
            poll_delay=0.05,
        )
        await worker.main()
        assert worker.jobs_complete == 1 and worker.jobs_failed == 0
    finally:
        await pool.flushdb()
        await pool.aclose()

    run_after = await db.scalar(
        select(SyncRun).where(SyncRun.id == run.id).execution_options(populate_existing=True)
    )
    assert run_after is not None and run_after.status == "done"
    assert await count(db, Team) == 12


# --------------------------------------------------------------------------- first-run ingest
async def test_empty_database_queues_one_full_nflverse_load(
    db: AsyncSession, ctx: dict[str, Any]
) -> None:
    from app.jobs.nfl_jobs import INITIAL_INGEST_JOB_ID, enqueue_initial_ingest

    queued: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    class FakeRedis:
        async def enqueue_job(self, *args: Any, **kwargs: Any) -> None:
            queued.append((args, kwargs))

    ctx["redis"] = FakeRedis()
    assert await enqueue_initial_ingest(ctx) is True
    # (function name, run_id=None, full=True): every season, tracked under a fixed job id
    assert queued == [
        (("ingest_nflverse_job", None, True), {"_job_id": INITIAL_INGEST_JOB_ID}),
    ]


async def test_existing_stats_mean_no_initial_load(db: AsyncSession, ctx: dict[str, Any]) -> None:
    from app.jobs.nfl_jobs import enqueue_initial_ingest

    db.add(
        PlayerWeekStats(
            gsis_id="00-1", season=2026, week=1, season_type="REG", position="WR", stats={}
        )
    )
    await db.commit()

    class FailingRedis:
        async def enqueue_job(self, *args: Any, **kwargs: Any) -> None:
            raise AssertionError("must not queue a load when data exists")

    ctx["redis"] = FailingRedis()
    assert await enqueue_initial_ingest(ctx) is False
