"""Projections end to end on the fixture league: compute -> freeze -> grade -> screens.

NFL data is synthetic but shaped like the real tables: every fixture player gets a gsis id,
eight weeks of history, and a week-9 game.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    League,
    LeagueMembership,
    NflGame,
    Player,
    PlayerWeekStats,
    Projection,
    ProjectionGrade,
    SyncRun,
    Team,
)
from app.jobs.league_jobs import sync_league_job
from app.jobs.tracking import create_run
from app.services.grading import grade_finished
from app.services.projections import compute_projections
from tests.conftest import auth_headers, make_user
from tests.sleeper_fixtures import LEAGUE_ID

pytestmark = pytest.mark.integration
# Kickoff is always in the future relative to the real clock, because the screens use "now"
# to decide which players are locked. The compute steps pass explicit times around it.
KICKOFF = datetime.now(UTC).replace(microsecond=0) + timedelta(days=2)
BEFORE, AFTER = KICKOFF - timedelta(days=2, minutes=5), KICKOFF + timedelta(hours=4)


async def seed_nfl(db: AsyncSession) -> None:
    """gsis ids for every player, 8 weeks of stats, and a week-9 game for every team."""
    await db.execute(update(Player).values(gsis_id="G" + Player.sleeper_id))
    players = (await db.scalars(select(Player))).all()
    teams = sorted({p.nfl_team for p in players if p.nfl_team})
    for i in range(0, len(teams) - 1, 2):
        db.add(NflGame(game_id=f"g{i}", season=2026, week=9, game_type="REG", home=teams[i],
                       away=teams[i + 1], kickoff_at=KICKOFF))  # fmt: skip
    rows = []
    for p in players:
        for wk in range(1, 9):
            stats = (
                {"points_allowed": 20.0, "def_sacks": 2.0}
                if p.position == "DEF"
                else {"receptions": 4.0, "receiving_yards": 50.0, "passing_yards": 0.0,
                      "rushing_yards": 20.0 if p.position == "RB" else 0.0}
            )  # fmt: skip
            if p.position == "QB":
                stats = {"passing_yards": 250.0, "passing_tds": 2.0}
            rows.append(
                PlayerWeekStats(gsis_id=p.gsis_id, season=2026, week=wk, season_type="REG",
                                position=p.position, team=p.nfl_team, opponent="XX",
                                stats=stats, offense_snap_pct=0.7)
            )  # fmt: skip
    db.add_all(rows)
    await db.commit()


@pytest.fixture
async def world(db: AsyncSession, ctx: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    league = League(platform="sleeper", external_id=LEAGUE_ID, season=2026, name="stub")
    db.add(league)
    await db.commit()
    run = await create_run(db, "sync_league", league_id=league.id)
    await sync_league_job(ctx, run.id, league.id)
    await seed_nfl(db)
    await db.refresh(league)
    user = await make_user(db, "ana@example.com")
    team = await db.scalar(select(Team).where(Team.league_id == league.id, Team.name == "Team 1"))
    assert team is not None
    db.add(LeagueMembership(user_id=user.id, league_id=league.id, my_team_id=team.id))
    await db.commit()
    await db.execute(delete(Projection))  # start each test without projections
    await db.commit()
    yield {"league": league, "user": user, "team": team}


async def test_projections_freeze_at_kickoff(db: AsyncSession, world: dict[str, Any]) -> None:
    league = world["league"]
    first = await compute_projections(db, league, 9, now=BEFORE)
    assert first["computed"] > 300
    before = {p.player_id: p.points for p in await db.scalars(select(Projection))}

    # New information arrives after kickoff: a monster week 8 for everyone.
    await db.execute(update(PlayerWeekStats).where(PlayerWeekStats.week == 8)
                     .values(stats={"receptions": 20.0, "receiving_yards": 300.0}))  # fmt: skip
    await db.commit()
    second = await compute_projections(db, league, 9, now=AFTER)

    db.expunge_all()
    after = {p.player_id: (p.points, p.frozen) for p in await db.scalars(select(Projection))}
    with_game = {pid for pid, (_, frozen) in after.items() if frozen}
    # Every player whose game started is frozen and unchanged; only players with no game
    # this week (bye: nothing to freeze) may be recomputed.
    assert second["frozen"] == len(with_game) and len(with_game) > 300
    assert second["computed"] == len(after) - len(with_game)
    assert {k: after[k][0] for k in with_game} == {k: before[k] for k in with_game}


async def test_grading_counts_only_genuine_predictions(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    league = world["league"]
    await compute_projections(db, league, 9, now=BEFORE)
    # One projection pretends it was computed after kickoff (e.g. a late data fix).
    late = await db.scalar(select(Projection).limit(1))
    assert late is not None
    late.computed_at = AFTER
    await db.execute(update(NflGame).values(home_score=21, away_score=17))  # games final
    await db.commit()

    graded = await grade_finished(db, 2026)
    assert graded > 300
    assert await grade_finished(db, 2026) == 0  # idempotent
    grades = {g.projection_id: g for g in await db.scalars(select(ProjectionGrade))}
    assert grades[late.id].genuine is False
    assert sum(g.genuine for g in grades.values()) == graded - 1

    resp = await client.get(
        f"/api/v1/leagues/{league.id}/accuracy", headers=auth_headers(world["user"].id)
    )
    body = resp.json()
    assert resp.status_code == 200 and body["n"] == graded - 1
    assert body["weeks"][0]["week"] == 9 and 0 <= body["coverage_80"] <= 1


async def test_matchup_and_lineup_screens(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    league, user = world["league"], world["user"]
    h = auth_headers(user.id)
    # Make one bench player clearly better than every starter: the lineup should start them.
    lineup = (await client.get(f"/api/v1/leagues/{league.id}/lineup?week=9", headers=h)).json()
    bench_wr = next(b for b in lineup["bench"] if b["position"] in ("WR", "RB"))
    gsis = await db.scalar(select(Player.gsis_id).where(Player.id == bench_wr["player_id"]))
    await db.execute(update(PlayerWeekStats).where(PlayerWeekStats.gsis_id == gsis)
                     .values(stats={"receptions": 12.0, "receiving_yards": 180.0,
                                    "receiving_tds": 2.0}))  # fmt: skip
    await db.commit()
    await compute_projections(db, league, 9, now=BEFORE)

    matchup = await client.get(f"/api/v1/leagues/{league.id}/matchup?week=9", headers=h)
    assert matchup.status_code == 200, matchup.text
    m = matchup.json()
    assert m["me"]["name"] == "Team 1" and m["opponent"] is not None
    assert len(m["me"]["starters"]) == 9
    assert all(s["projection"] is not None for s in m["me"]["starters"])
    assert 0 <= m["outlook"]["win_probability"] <= 1
    assert m["unsupported_rules"] == ["def_st_ff", "def_st_fum_rec", "st_ff", "st_fum_rec"]

    lineup = (await client.get(f"/api/v1/leagues/{league.id}/lineup?week=9", headers=h)).json()
    assert lineup["optimal_points"] > lineup["current_points"]
    ins = [s["player_in"]["player_id"] for s in lineup["swaps"]]
    assert bench_wr["player_id"] in ins
    swap = next(s for s in lineup["swaps"] if s["player_in"]["player_id"] == bench_wr["player_id"])
    assert swap["player_out"] is not None and swap["gain"] > 0
    assert lineup["win_probability_optimal"] >= lineup["win_probability_current"]

    detail = await client.get(
        f"/api/v1/players/{bench_wr['player_id']}/projection?league_id={league.id}&week=9",
        headers=h,
    )
    d = detail.json()
    assert detail.status_code == 200
    assert d["factors"][0]["name"] == "baseline"
    assert len(d["recent_games"]) == 4 and d["recent_games"][0]["week"] == 8


async def test_screens_need_my_team(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    await db.execute(update(LeagueMembership).values(my_team_id=None))
    await db.commit()
    resp = await client.get(
        f"/api/v1/leagues/{world['league'].id}/matchup", headers=auth_headers(world["user"].id)
    )
    assert resp.status_code == 409 and resp.json()["code"] == "team_not_chosen"


async def test_player_projection_is_tenant_scoped(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    """The league is a query parameter here, so the path-based isolation test can't see it."""
    stranger = await make_user(db, "stranger@example.com")
    player_id = await db.scalar(select(Player.id).limit(1))
    resp = await client.get(
        f"/api/v1/players/{player_id}/projection?league_id={world['league'].id}",
        headers=auth_headers(stranger.id),
    )
    assert resp.status_code == 404 and resp.json()["code"] == "league_not_found"
    assert (await db.scalars(select(SyncRun))).all()  # (world fixture really synced)


# --------------------------------------------------------------------------- edge cases (step 14)
async def test_players_whose_games_have_started_are_locked_in_lineup_advice(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    """Once a game kicks off you can't change that player in Sleeper, so the app never
    suggests moving anyone in or out, and the win chance doesn't pretend you can."""
    league, h = world["league"], auth_headers(world["user"].id)
    await compute_projections(db, league, 9, now=BEFORE)
    started = datetime.now(UTC) - timedelta(hours=1)  # kicked off an hour ago, not final
    await db.execute(update(NflGame).values(kickoff_at=started, home_score=None, away_score=None))
    await db.commit()

    lineup = (await client.get(f"/api/v1/leagues/{league.id}/lineup?week=9", headers=h)).json()
    statuses = {p["game_status"] for p in lineup["starters"] + lineup["bench"]}
    assert statuses <= {"in_progress", "bye"} and "in_progress" in statuses
    assert lineup["swaps"] == []  # everyone with a game is locked
    assert lineup["win_probability_optimal"] == lineup["win_probability_current"]

    matchup = (await client.get(f"/api/v1/leagues/{league.id}/matchup?week=9", headers=h)).json()
    assert all(p["actual_points"] is None for p in matchup["me"]["starters"])  # no results yet


async def test_a_league_still_on_its_first_sync_says_so(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    await db.execute(update(League).values(current_week=None))
    await db.commit()
    resp = await client.get(
        f"/api/v1/leagues/{world['league'].id}/matchup", headers=auth_headers(world["user"].id)
    )
    assert resp.status_code == 409 and resp.json()["code"] == "not_synced"


async def test_missing_players_and_bad_weeks_get_clear_errors(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    lid, h = world["league"].id, auth_headers(world["user"].id)
    gone = await client.get(f"/api/v1/players/999999/projection?league_id={lid}", headers=h)
    assert gone.status_code == 404 and gone.json()["code"] == "player_not_found"
    for bad in (0, 19):
        resp = await client.get(f"/api/v1/leagues/{lid}/matchup?week={bad}", headers=h)
        assert resp.status_code == 422 and resp.json()["code"] == "invalid", bad


async def test_a_week_without_stored_rosters_returns_empty_lists_not_an_error(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    """The web app turns this into "Week 18 isn't here yet"; it relies on 200 + empty."""
    lid, h = world["league"].id, auth_headers(world["user"].id)
    lineup = (await client.get(f"/api/v1/leagues/{lid}/lineup?week=18", headers=h)).json()
    assert lineup["starters"] == [] and lineup["bench"] == [] and lineup["swaps"] == []
    matchup = (await client.get(f"/api/v1/leagues/{lid}/matchup?week=18", headers=h)).json()
    assert matchup["me"]["starters"] == [] and matchup["opponent"] is None
    assert matchup["outlook"] is None


async def test_accuracy_is_empty_not_an_error_before_anything_is_graded(
    db: AsyncSession, world: dict[str, Any], client: httpx.AsyncClient
) -> None:
    body = (
        await client.get(
            f"/api/v1/leagues/{world['league'].id}/accuracy",
            headers=auth_headers(world["user"].id),
        )
    ).json()
    assert body["n"] == 0 and body["mae"] is None and body["weeks"] == []


async def test_grades_use_the_leagues_own_scoring_on_the_real_stat_line(
    db: AsyncSession, world: dict[str, Any]
) -> None:
    league = world["league"]
    await compute_projections(db, league, 9, now=BEFORE)
    player = await db.scalar(
        select(Player).join(Projection, Projection.player_id == Player.id)
        .where(Player.position == "WR", Player.gsis_id.is_not(None)).limit(1)
    )  # fmt: skip
    assert player is not None and player.gsis_id is not None
    # 4 catches for 100 yards under the fixture league's half-PPR rules: 4 * 0.5 + 100 * 0.1
    db.add(PlayerWeekStats(gsis_id=player.gsis_id, season=2026, week=9, season_type="REG",
                           position="WR", team=player.nfl_team, opponent="XX",
                           stats={"receptions": 4.0, "receiving_yards": 100.0}))  # fmt: skip
    await db.execute(update(NflGame).values(home_score=21, away_score=17))
    await db.commit()

    assert await grade_finished(db, 2026) > 0
    graded = await db.scalar(
        select(ProjectionGrade.actual_points)
        .join(Projection, Projection.id == ProjectionGrade.projection_id)
        .where(Projection.player_id == player.id)
    )
    assert graded == pytest.approx(12.0)
    assert await grade_finished(db, 2026) == 0  # nothing left to grade
