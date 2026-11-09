"""ARQ job functions for leagues. Thin: tracking + calling services.

ARQ passes `ctx` (a dict) first. The worker's startup fills it with:
  ctx["sessionmaker"]: async_sessionmaker   ctx["adapters"]: {"sleeper": SleeperAdapter}
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import LeagueAdapter, NflState
from app.db.models import League, LeagueMembership, PlatformAccount, SyncRun
from app.jobs.tracking import create_run, run_tracked
from app.services.projections import compute_projections
from app.services.sync import players_are_stale, sync_league, upsert_platform_players

Ctx = dict[str, Any]


def _sleeper(ctx: Ctx) -> LeagueAdapter:
    adapter: LeagueAdapter = ctx["adapters"]["sleeper"]
    return adapter


def season_week(state: NflState) -> tuple[int, int]:
    """The week to treat as 'current'. Off-season/preseason clamps to week 1."""
    week = state.week if state.season_type == "regular" else 1
    return state.season, max(1, week)


async def connect_sleeper(ctx: Ctx, run_id: int, user_id: int, username: str) -> dict[str, Any]:
    """Find a Sleeper user's leagues for the current season and link the account."""
    adapter = _sleeper(ctx)

    async def body(db: AsyncSession) -> dict[str, Any]:
        state = await adapter.fetch_state()
        season, _ = season_week(state)
        su = await adapter.find_user(username)
        leagues = await adapter.find_leagues(su, season)
        stmt = insert(PlatformAccount).values(
            user_id=user_id,
            platform="sleeper",
            external_user_id=su.external_user_id,
            display_name=su.username,
        )
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[PlatformAccount.user_id, PlatformAccount.platform],
                set_={
                    "external_user_id": stmt.excluded.external_user_id,
                    "display_name": stmt.excluded.display_name,
                },
            )
        )
        await db.commit()
        return {
            "username": su.username,
            "sleeper_user_id": su.external_user_id,
            "season": season,
            "leagues": [
                {
                    "external_id": lg.external_id,
                    "name": lg.name,
                    "season": lg.season,
                    "total_teams": lg.total_teams,
                }
                for lg in leagues
            ],
        }

    result = await run_tracked(ctx["sessionmaker"], run_id, body, job_try=ctx.get("job_try", 1))
    assert result is not None
    return result


async def sync_league_job(ctx: Ctx, run_id: int, league_id: int) -> dict[str, Any]:
    """Refresh one league. First sync also back-fills every past week of the season."""
    adapter = _sleeper(ctx)

    async def body(db: AsyncSession) -> dict[str, Any]:
        league = await db.get(League, league_id)
        if league is None:
            raise LookupError(f"league {league_id} not found")
        state = await adapter.fetch_state()
        season, week = season_week(state)
        if season != league.season:
            # A past season's league: its final week is the last one with games.
            week = 17
        if await players_are_stale(db):
            await upsert_platform_players(db, "sleeper", await adapter.fetch_players())
        history = range(1, week) if league.last_synced_at is None else [w for w in (week - 1,) if w]
        synced = await sync_league(
            db, adapter, league.external_id, current_week=week, history_weeks=history
        )
        projected = await compute_projections(db, synced, week)
        return {"league_id": synced.id, "week": week, **projected}

    result = await run_tracked(ctx["sessionmaker"], run_id, body, job_try=ctx.get("job_try", 1))
    assert result is not None
    return result


async def sync_players_job(ctx: Ctx) -> int:
    """Daily refresh of the Sleeper player list (names, teams, injury status)."""
    async with ctx["sessionmaker"]() as db:
        return await upsert_platform_players(db, "sleeper", await _sleeper(ctx).fetch_players())


async def sync_all_leagues(ctx: Ctx) -> int:
    """Hourly cron: enqueue a sync for every league somebody follows (skip ones already queued)."""
    async with ctx["sessionmaker"]() as db:
        league_ids = (await db.scalars(select(LeagueMembership.league_id).distinct())).all()
        busy = set(
            (
                await db.scalars(
                    select(SyncRun.league_id).where(
                        SyncRun.kind == "sync_league", SyncRun.status.in_(("queued", "running"))
                    )
                )
            ).all()
        )
        count = 0
        for lid in league_ids:
            if lid in busy:
                continue
            run = await create_run(db, "sync_league", league_id=lid)
            await ctx["redis"].enqueue_job("sync_league_job", run.id, lid, _job_id=run.job_id)
            count += 1
    return count
