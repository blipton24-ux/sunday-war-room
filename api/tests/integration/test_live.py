"""Live game day (P2 step 7, ADR-044/045): the every-minute tick and the live Matchup view."""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LiveGame, Matchup, NflGame, Player, RosterEntry
from app.services.live import live_update
from app.services.projections import compute_projections
from app.sources.espn_scoreboard import GameStatus, ScoreboardError
from tests.conftest import auth_headers
from tests.integration.test_projections_and_views import BEFORE, KICKOFF

pytestmark = pytest.mark.integration
SEASON, WEEK = 2026, 9


def status(home: str, away: str, state: str, remaining: float) -> GameStatus:
    """A GameStatus whose remaining_fraction is `remaining` (quarter + clock worked out)."""
    seconds = remaining * 3600
    period = 4 - int(seconds // 900) if state == "in_progress" else (4 if state == "final" else 0)
    clock = seconds - (4 - period) * 900 if state == "in_progress" else 0.0
    return GameStatus(
        espn_id=f"x{home}", season=SEASON, week=WEEK, home=home, away=away,
        kickoff_at=KICKOFF, state=state,  # type: ignore[arg-type]
        period=period, clock_seconds=clock,
        detail="4:12 - 3rd" if state == "in_progress" else "Final",
        home_score=14, away_score=7, possession=home if state == "in_progress" else None,
    )  # fmt: skip


async def my_starters(db: AsyncSession, w: dict[str, Any]) -> list[Player]:
    ids = await db.scalars(
        select(RosterEntry.player_id).where(
            RosterEntry.team_id == w["team"].id, RosterEntry.week == WEEK, RosterEntry.is_starter
        )
    )
    return list((await db.scalars(select(Player).where(Player.id.in_(list(ids))))).all())


# --------------------------------------------------------------------------- the tick
async def test_quiet_outside_game_windows(
    db: AsyncSession, ctx: dict[str, Any], world: dict[str, Any]
) -> None:
    calls: list[tuple[int, int]] = []

    async def fetch(season: int, week: int) -> list[GameStatus]:
        calls.append((season, week))
        return []

    far_from_kickoff = KICKOFF - timedelta(days=1)
    result = await live_update(db, ctx["adapters"]["sleeper"], fetch, now=far_from_kickoff)
    assert result == {"skipped": "no games now"} and calls == []


async def test_tick_during_games_stores_clocks_and_points(
    db: AsyncSession, ctx: dict[str, Any], world: dict[str, Any]
) -> None:
    game = await db.scalar(select(NflGame).where(NflGame.week == WEEK))
    assert game is not None

    async def fetch(season: int, week: int) -> list[GameStatus]:
        return [status(game.home, game.away, "in_progress", 0.32)]

    await db.execute(update(Matchup).values(home_player_points={}, away_player_points={}))
    await db.commit()
    result = await live_update(
        db, ctx["adapters"]["sleeper"], fetch, now=KICKOFF + timedelta(hours=1)
    )
    assert result == {"season": SEASON, "week": WEEK, "leagues": 1, "scoreboard": True}

    stored = await db.scalar(select(LiveGame).where(LiveGame.home == game.home))
    assert stored is not None and stored.state == "in_progress"
    assert stored.remaining_fraction == pytest.approx(0.32)
    rows = (await db.scalars(select(Matchup).where(Matchup.week == WEEK))).all()
    assert all(m.home_player_points for m in rows), "per-player points from Sleeper"
    assert all(m.updated_at is not None for m in rows)


async def test_scoreboard_down_still_updates_points(
    db: AsyncSession, ctx: dict[str, Any], world: dict[str, Any]
) -> None:
    async def broken(season: int, week: int) -> list[GameStatus]:
        raise ScoreboardError("down")

    result = await live_update(
        db, ctx["adapters"]["sleeper"], broken, now=KICKOFF + timedelta(hours=1)
    )
    assert result["scoreboard"] is False and result["leagues"] == 1


# --------------------------------------------------------------------------- the screen
async def live_world(db: AsyncSession, w: dict[str, Any], *, with_clock: bool) -> list[Player]:
    """My starters' games live (a third left), each starter with 5 points so far."""
    league = w["league"]
    await compute_projections(db, league, WEEK, now=BEFORE)
    starters = await my_starters(db, w)
    await db.execute(update(NflGame).where(NflGame.week == WEEK).values(
        kickoff_at=datetime.now(UTC) - timedelta(hours=2)))  # fmt: skip
    await db.execute(delete(LiveGame))
    if with_clock:
        for g in (await db.scalars(select(NflGame).where(NflGame.week == WEEK))).all():
            # every game this week is on the scoreboard, a third left
            s = status(g.home, g.away, "in_progress", 1 / 3)
            db.add(LiveGame(espn_id=s.espn_id, season=SEASON, week=WEEK, home=g.home,
                            away=g.away, kickoff_at=s.kickoff_at, state=s.state,
                            period=s.period, clock_seconds=s.clock_seconds, detail=s.detail,
                            home_score=14, away_score=7, possession=g.home,
                            remaining_fraction=s.remaining_fraction,
                            updated_at=datetime.now(UTC)))  # fmt: skip
    points = {str(p.id): 5.0 for p in starters}
    await db.execute(update(Matchup).where(Matchup.week == WEEK).values(
        home_player_points=points, away_player_points=points))  # fmt: skip
    await db.commit()
    return starters


async def test_live_matchup_blends_points_so_far_with_time_left(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    await live_world(db, world, with_clock=True)
    h = auth_headers(world["user"].id)
    body = (
        await client.get(f"/api/v1/leagues/{world['league'].id}/matchup?week=9", headers=h)
    ).json()
    assert body["live"] is True and body["clock_source"] == "scoreboard"
    assert body["scores_updated_at"] is not None
    live = [s for s in body["me"]["starters"] if s["game_status"] == "in_progress"]
    assert live
    for s in live:
        assert s["live_points"] == 5.0 and s["game_detail"] == "4:12 - 3rd"
        assert s["remaining_fraction"] == pytest.approx(1 / 3, abs=0.01)
    # Projected total = 5 so far + a third of each projection.
    expected = sum(5.0 + (s["projection"]["points"] if s["projection"] else 0) / 3 for s in live)
    assert body["me"]["projected_total"] == pytest.approx(expected, abs=0.1)
    assert any(s["has_ball"] for s in live)
    assert 0.0 <= body["outlook"]["win_probability"] <= 1.0


async def test_without_the_scoreboard_time_left_comes_from_kickoff(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    await live_world(db, world, with_clock=False)
    h = auth_headers(world["user"].id)
    body = (
        await client.get(f"/api/v1/leagues/{world['league'].id}/matchup?week=9", headers=h)
    ).json()
    assert body["live"] is True and body["clock_source"] == "kickoff_estimate"
    s = next(s for s in body["me"]["starters"] if s["game_status"] == "in_progress")
    assert s["remaining_fraction"] == pytest.approx(1 / 3, abs=0.02)  # 2h into ~3h
    assert s["game_detail"] is None


async def test_final_game_uses_platform_points_until_nflverse_publishes(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    starters = await live_world(db, world, with_clock=True)
    await db.execute(update(LiveGame).values(state="final", remaining_fraction=0.0, detail="Final"))
    await db.commit()
    h = auth_headers(world["user"].id)
    body = (
        await client.get(f"/api/v1/leagues/{world['league'].id}/matchup?week=9", headers=h)
    ).json()
    finals = [s for s in body["me"]["starters"] if s["game_status"] == "final"]
    assert len(finals) == len([p for p in starters if p.nfl_team])
    assert all(s["actual_points"] == 5.0 for s in finals)
    assert body["live"] is False and body["clock_source"] is None
