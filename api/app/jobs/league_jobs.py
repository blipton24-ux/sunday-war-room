"""ARQ job functions for leagues. Thin: tracking + calling services.

ARQ passes `ctx` (a dict) first. The worker's startup fills it with:
  ctx["sessionmaker"]: async_sessionmaker   ctx["adapters"]: {"sleeper": SleeperAdapter}
Adapters are looked up through app.adapters.registry, never by reaching into ctx directly.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import (
    AuthRequired,
    CredentialsInvalid,
    LeagueAdapter,
    NflState,
    UnsupportedLeague,
)
from app.adapters.espn import EspnAccess
from app.adapters.registry import adapter_for, espn_for, nfl_source, sleeper_discovery
from app.db.models import League, LeagueMembership, PlatformAccount, SyncRun
from app.jobs.tracking import create_run, run_tracked
from app.logging import get_logger
from app.services.credentials import (
    NEEDS_RECONNECT,
    OK,
    decrypt_espn,
    espn_candidates,
    set_status,
)
from app.services.live import live_update
from app.services.projections import (
    compute_projections,
    compute_rest_of_season,
    projection_pool,
)
from app.services.sync import players_are_stale, sync_league, upsert_platform_players
from app.sources.espn_scoreboard import fetch_week

Ctx = dict[str, Any]


async def read_league[T](
    ctx: Ctx, db: AsyncSession, league: League, work: Callable[[LeagueAdapter], Awaitable[T]]
) -> T:
    """Run `work` with an adapter that can read this league.

    Sleeper needs no login. A private ESPN league is read with a follower's cookies (best first);
    cookies the platform refuses are marked for reconnect and the next follower's are tried
    (ADR-051). When none work, CredentialsInvalid says everyone must reconnect.
    """
    if league.platform != "espn":
        return await work(adapter_for(ctx, league.platform))  # type: ignore[arg-type]
    failure: CredentialsInvalid | None = None
    # Plain ids, read up front: a rollback expires every loaded object, and an expired object
    # can't be read again in async code. Accounts are reloaded fresh when they need updating.
    attempts = [
        (c.account.id if c.account else None, c.access) for c in await espn_candidates(db, league)
    ]
    for account_id, access in attempts:
        try:
            result = await work(adapter_for(ctx, "espn", access))
        except CredentialsInvalid as exc:
            await db.rollback()
            await _mark(db, account_id, NEEDS_RECONNECT)
            failure = exc
            continue
        await _mark(db, account_id, OK, only_if_not=OK)
        return result
    raise failure or CredentialsInvalid("Every follower of this ESPN league needs to reconnect")


async def _mark(
    db: AsyncSession, account_id: int | None, status: str, *, only_if_not: str | None = None
) -> None:
    """Set a platform account's status (reloading it, so it is safe after a rollback)."""
    if account_id is None:
        return
    account = await db.get(PlatformAccount, account_id)
    if account is not None and account.status != only_if_not:
        await set_status(db, account, status)


def season_week(state: NflState) -> tuple[int, int]:
    """The week to treat as 'current'. Off-season/preseason clamps to week 1."""
    week = state.week if state.season_type == "regular" else 1
    return state.season, max(1, week)


async def connect_sleeper(ctx: Ctx, run_id: int, user_id: int, username: str) -> dict[str, Any]:
    """Find a Sleeper user's leagues for the current season and link the account."""
    source = nfl_source(ctx)
    finder = sleeper_discovery(ctx)

    async def body(db: AsyncSession) -> dict[str, Any]:
        state = await source.fetch_state()
        season, _ = season_week(state)
        su = await finder.find_user(username)
        leagues = await finder.find_leagues(su, season)
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


async def connect_espn(ctx: Ctx, run_id: int, user_id: int, account_id: int) -> dict[str, Any]:
    """List the ESPN football leagues a user's saved cookies belong to this season (ADR-051).

    Only the account id travels through the queue: the cookies are read (and decrypted) here, from
    the database, because job arguments are stored unencrypted in Redis.
    """
    source = nfl_source(ctx)

    async def body(db: AsyncSession) -> dict[str, Any]:
        account = await db.get(PlatformAccount, account_id)
        if account is None or account.user_id != user_id or account.platform != "espn":
            raise LookupError(f"ESPN account {account_id} not found")
        season, _ = season_week(await source.fetch_state())
        adapter = espn_for(ctx, EspnAccess(season, decrypt_espn(account)))
        try:
            found = await adapter.find_leagues()
        except CredentialsInvalid:
            await set_status(db, account, NEEDS_RECONNECT)
            raise
        await set_status(db, account, OK)
        return {
            "via": "cookies",
            "account_id": account.id,
            "season": season,
            "leagues": [
                {
                    "external_id": ref.external_id,
                    "name": ref.name,
                    "season": ref.season,
                    "total_teams": ref.total_teams,
                    "team_id": team_id,  # ESPN says which team is the user's: preselect it
                }
                for ref, team_id in found
            ],
        }

    result = await run_tracked(ctx["sessionmaker"], run_id, body, job_try=ctx.get("job_try", 1))
    assert result is not None
    return result


async def probe_espn(
    ctx: Ctx, run_id: int, user_id: int, league_id: str, season: int | None
) -> dict[str, Any]:
    """Ask ESPN once, with no cookies, whether a pasted league is public (ADR-051).

    Public: the league and its teams are returned so the user can pick theirs. Private: the
    result says so and the screen asks for the cookies. A league type we can't score is reported
    in plain words. An unknown league fails the run.
    """
    source = nfl_source(ctx)

    async def body(db: AsyncSession) -> dict[str, Any]:
        current, _ = season_week(await source.fetch_state())
        use_season = season or current
        adapter = espn_for(ctx, EspnAccess(use_season, None))
        try:
            _, name, teams = await adapter.probe(league_id)
        except AuthRequired:
            return {"private": True, "external_id": league_id, "season": use_season}
        except UnsupportedLeague as exc:
            return {"unsupported": str(exc), "external_id": league_id, "season": use_season}
        return {
            "public": True,
            "via": "link",
            "season": use_season,
            "leagues": [
                {
                    "external_id": league_id,
                    "name": name,
                    "season": use_season,
                    "total_teams": len(teams),
                    "team_id": None,
                }
            ],
            "teams": [{"external_id": tid, "name": tname} for tid, tname in teams],
        }

    result = await run_tracked(ctx["sessionmaker"], run_id, body, job_try=ctx.get("job_try", 1))
    assert result is not None
    return result


async def sync_league_job(ctx: Ctx, run_id: int, league_id: int) -> dict[str, Any]:
    """Refresh one league. First sync also back-fills every past week of the season."""
    source = nfl_source(ctx)

    async def body(db: AsyncSession) -> dict[str, Any]:
        league = await db.get(League, league_id)
        if league is None:
            raise LookupError(f"league {league_id} not found")
        state = await source.fetch_state()
        season, week = season_week(state)
        if season != league.season:
            # A past season's league: its final week is the last one with games.
            week = 17
        if await players_are_stale(db):
            # Sleeper's list is the master list for every platform (ADR-053).
            await upsert_platform_players(db, "sleeper", await source.fetch_players())
        history = range(1, week) if league.last_synced_at is None else [w for w in (week - 1,) if w]
        external_id = league.external_id  # read now: a failed attempt's rollback expires `league`
        synced = await read_league(
            ctx,
            db,
            league,
            lambda adapter: sync_league(
                db, adapter, external_id, current_week=week, history_weeks=history
            ),
        )
        pool = await projection_pool(db, synced, week)
        projected = await compute_projections(db, synced, week, player_ids=pool)
        ros = await compute_rest_of_season(db, synced, week, pool)
        return {"league_id": synced.id, "week": week, **projected, "rest_of_season": ros}

    result = await run_tracked(ctx["sessionmaker"], run_id, body, job_try=ctx.get("job_try", 1))
    assert result is not None
    return result


async def sync_players_job(ctx: Ctx) -> int:
    """Daily refresh of the Sleeper player list (names, teams, injury status)."""
    async with ctx["sessionmaker"]() as db:
        return await upsert_platform_players(db, "sleeper", await nfl_source(ctx).fetch_players())


async def sync_all_leagues(ctx: Ctx) -> int:
    """Hourly cron: enqueue a sync for every league somebody follows (skip ones already queued)."""
    async with ctx["sessionmaker"]() as db:
        leagues = (
            await db.scalars(
                select(League).where(League.id.in_(select(LeagueMembership.league_id)))
            )
        ).all()
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
        for league in leagues:
            lid = league.id
            if lid in busy:
                continue
            # A private league whose followers all need to reconnect can't be read: skip it
            # rather than failing every hour (it resumes the moment someone reconnects).
            if league.platform == "espn" and not await espn_candidates(db, league):
                continue
            run = await create_run(db, "sync_league", league_id=lid)
            await ctx["redis"].enqueue_job("sync_league_job", run.id, lid, _job_id=run.job_id)
            count += 1
    return count


async def live_update_job(ctx: Ctx) -> dict[str, Any]:
    """Every minute (P2, ADR-045): fresh scores and game clocks, but only while games are on."""
    async with ctx["sessionmaker"]() as db:
        used: dict[int, int | None] = {}  # league id -> account whose cookies this tick used

        async def resolve(league: League) -> LeagueAdapter | None:
            if league.platform != "espn":
                return adapter_for(ctx, league.platform)  # type: ignore[arg-type]
            candidates = await espn_candidates(db, league)
            if not candidates:  # every follower needs to reconnect: nothing to read with
                return None
            first = candidates[0]
            used[league.id] = first.account.id if first.account else None
            return adapter_for(ctx, "espn", first.access)

        async def invalid(league_id: int) -> None:
            await _mark(db, used.get(league_id), NEEDS_RECONNECT)

        result = await live_update(
            db, nfl_source(ctx), lambda s, w: fetch_week(s, w), resolve=resolve, on_invalid=invalid
        )
    if "skipped" not in result:
        get_logger("live").info("live_update", **result)
    return result
