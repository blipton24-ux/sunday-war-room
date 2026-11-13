"""Rest-of-season projections stored for a league's player pool (P2 step 2)."""

from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NflGame, Player, RestOfSeasonProjection
from app.jobs.league_jobs import sync_league_job
from app.jobs.tracking import create_run
from app.model.rest_of_season import PLAYOFF_WEIGHT
from app.services.projections import (
    ROS_MODEL_VERSION,
    compute_rest_of_season,
    league_player_ids,
    projection_pool,
)
from tests.integration.test_projections_and_views import KICKOFF

pytestmark = pytest.mark.integration


async def seed_rest_of_season_schedule(db: AsyncSession) -> str:
    """Weeks 10-17 for every team, with one team on bye in week 12. Returns that team."""
    players = (await db.scalars(select(Player))).all()
    teams = sorted({p.nfl_team for p in players if p.nfl_team})
    bye_team = teams[0]
    for week in range(10, 18):
        playing = [t for t in teams if not (week == 12 and t == bye_team)]
        for i in range(0, len(playing) - 1, 2):
            db.add(NflGame(game_id=f"w{week}g{i}", season=2026, week=week, game_type="REG",
                           home=playing[i], away=playing[i + 1], kickoff_at=KICKOFF))  # fmt: skip
    await db.commit()
    return bye_team


async def test_pool_is_rostered_players_plus_realistic_free_agents(
    db: AsyncSession, world: dict[str, Any]
) -> None:
    league = world["league"]
    rostered = await league_player_ids(db, league.id, 9)
    pool = await projection_pool(db, league, 9)
    assert rostered < pool  # strictly more: the fixture's free agents are included
    free_agents = (await db.scalars(select(Player).where(Player.id.in_(pool - rostered)))).all()
    assert free_agents and all(p.nfl_team and p.position for p in free_agents)


async def test_rest_of_season_through_the_playoffs(db: AsyncSession, world: dict[str, Any]) -> None:
    league = world["league"]
    bye_team = await seed_rest_of_season_schedule(db)
    pool = await projection_pool(db, league, 9)

    for _ in range(2):  # idempotent
        written = await compute_rest_of_season(db, league, 9, pool)
    assert written == len(pool)
    rows = (await db.scalars(select(RestOfSeasonProjection))).all()
    assert len(rows) == len(pool)
    assert {(r.from_week, r.horizon_key, r.model_version) for r in rows} == {
        (9, "17:15", ROS_MODEL_VERSION)  # fixture league: playoffs weeks 15-17, 8 teams
    }

    r = next(r for r in rows if r.points > 0)
    assert [w["week"] for w in r.weekly] == list(range(9, 18))
    weights = {w["week"]: w["weight"] for w in r.weekly}
    assert weights[14] == 1.0 and weights[15] == PLAYOFF_WEIGHT
    assert r.points == pytest.approx(sum(w["points"] * w["weight"] for w in r.weekly), abs=0.05)

    team_of = dict((await db.execute(select(Player.id, Player.nfl_team))).tuples().all())
    on_bye = next(r for r in rows if team_of[r.player_id] == bye_team)
    week12 = next(w for w in on_bye.weekly if w["week"] == 12)
    assert week12["points"] == 0.0 and week12["opponent"] is None
    assert on_bye.games == 8  # 9 weeks, one bye


async def test_a_new_week_replaces_the_old_rows(db: AsyncSession, world: dict[str, Any]) -> None:
    league = world["league"]
    await seed_rest_of_season_schedule(db)
    pool = await projection_pool(db, league, 9)
    await compute_rest_of_season(db, league, 9, pool)
    await compute_rest_of_season(db, league, 10, pool)
    weeks = set(await db.scalars(select(RestOfSeasonProjection.from_week).distinct()))
    assert weeks == {10}


async def test_sync_job_computes_rest_of_season(
    db: AsyncSession, ctx: dict[str, Any], world: dict[str, Any]
) -> None:
    league = world["league"]
    run = await create_run(db, "sync_league", league_id=league.id)
    result = await sync_league_job(ctx, run.id, league.id)
    assert result["rest_of_season"] > 0
    stored = await db.scalar(select(func.count()).select_from(RestOfSeasonProjection))
    assert stored == result["rest_of_season"]
