"""Live game day (P2, ADR-044/045): keep game state and fantasy points fresh during games.

A worker job calls `live_update` every minute. Outside game windows it returns at once without
touching the network. Inside one it reads ESPN's scoreboard once (game clocks) and each
followed league's matchup once (fantasy points), for everyone; screens then poll the API.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import LeagueAdapter, NflSource
from app.db.models import League, LeagueMembership, LiveGame, NflGame
from app.logging import get_logger
from app.services.sync import refresh_live_matchups
from app.sources.espn_scoreboard import GameStatus, ScoreboardError

log = get_logger("live")

BEFORE_KICKOFF = timedelta(minutes=10)
GAME_LENGTH = timedelta(hours=4, minutes=30)  # generous: delays and overtime

FetchWeek = Callable[[int, int], Awaitable[list[GameStatus]]]


async def games_in_window(db: AsyncSession, season: int, week: int, now: datetime) -> int:
    """How many of this week's games are about to start, live, or just finished."""
    games = await db.scalars(
        select(NflGame).where(
            NflGame.season == season,
            NflGame.week == week,
            NflGame.kickoff_at.is_not(None),
            NflGame.kickoff_at <= now + BEFORE_KICKOFF,
            NflGame.kickoff_at >= now - GAME_LENGTH,
        )
    )
    return len(games.all())


async def store_scoreboard(db: AsyncSession, games: Sequence[GameStatus], now: datetime) -> None:
    for g in games:
        values: dict[str, Any] = {
            "espn_id": g.espn_id,
            "season": g.season,
            "week": g.week,
            "home": g.home,
            "away": g.away,
            "kickoff_at": g.kickoff_at,
            "state": g.state,
            "period": g.period,
            "clock_seconds": g.clock_seconds,
            "detail": g.detail,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "possession": g.possession,
            "remaining_fraction": g.remaining_fraction,
            "updated_at": now,
        }
        stmt = insert(LiveGame).values(**values)
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[LiveGame.season, LiveGame.week, LiveGame.home],
                set_={
                    k: getattr(stmt.excluded, k)
                    for k in values
                    if k not in ("season", "week", "home")
                },
            )
        )
    await db.commit()


async def live_update(
    db: AsyncSession,
    adapter: NflSource,
    fetch_week: FetchWeek,
    *,
    now: datetime | None = None,
    resolve: Callable[[League], LeagueAdapter | None] | None = None,
) -> dict[str, Any]:
    """One live tick. Returns what it did (logged by the job).

    `adapter` supplies the NFL clock. `resolve` picks the adapter that reads each league's scores
    by platform; without it every league is read through `adapter` (a Sleeper-only setup).
    """
    now = now or datetime.now(UTC)
    state = await adapter.fetch_state()
    if state.season_type != "regular" and state.season_type != "post":
        return {"skipped": "offseason"}
    season, week = state.season, state.week
    if await games_in_window(db, season, week, now) == 0:
        return {"skipped": "no games now"}

    scoreboard_ok = True
    try:
        await store_scoreboard(db, await fetch_week(season, week), now)
    except ScoreboardError as exc:  # the clock part is optional (ADR-044)
        scoreboard_ok = False
        log.warning("scoreboard_unavailable", error=str(exc))

    leagues = (
        await db.scalars(
            select(League)
            .where(League.season == season)
            .where(League.id.in_(select(LeagueMembership.league_id)))
        )
    ).all()
    updated = 0
    for league in leagues:
        try:
            reader = resolve(league) if resolve else cast(LeagueAdapter, adapter)
            if reader is None:  # no usable adapter (e.g. credentials need reconnecting)
                continue
            await refresh_live_matchups(db, reader, league, week)
            updated += 1
        except Exception as exc:  # one bad league must not stop the others
            await db.rollback()
            log.warning("live_league_failed", league_id=league.id, error=str(exc))
    return {"season": season, "week": week, "leagues": updated, "scoreboard": scoreboard_ok}


async def live_games_for_week(db: AsyncSession, season: int, week: int) -> dict[str, LiveGame]:
    """team -> its live game record this week (both teams map to the same row)."""
    rows = await db.scalars(
        select(LiveGame).where(LiveGame.season == season, LiveGame.week == week)
    )
    out: dict[str, LiveGame] = {}
    for g in rows:
        out[g.home] = g
        out[g.away] = g
    return out
