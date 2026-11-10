"""Waivers endpoint end to end on the fixture league (P2 step 4, ADR-047)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import League, LeagueMembership, Player, PlayerWeekStats, RosterEntry, Team
from app.services.projections import compute_projections, compute_rest_of_season, projection_pool
from app.services.waivers import waivers_view
from tests.conftest import auth_headers, make_user
from tests.integration.test_projections_and_views import BEFORE
from tests.integration.test_rest_of_season_integration import seed_rest_of_season_schedule

pytestmark = pytest.mark.integration
BREAKOUT = "12457"  # Jaydon Blue, RB: a free agent in the fixture (dropped in week 9)


@pytest.fixture
async def projected(db: AsyncSession, world: dict[str, Any]) -> dict[str, Any]:
    league = world["league"]
    await seed_rest_of_season_schedule(db)
    # In the synthetic data every RB scores the same; make one free agent clearly better.
    breakout = await db.scalar(select(Player).where(Player.sleeper_id == BREAKOUT))
    assert breakout is not None
    await db.execute(
        update(PlayerWeekStats)
        .where(PlayerWeekStats.gsis_id == breakout.gsis_id)
        .values(stats={"rushing_yards": 120.0, "rushing_tds": 1.0, "receptions": 5.0,
                       "receiving_yards": 40.0})
    )  # fmt: skip
    await db.commit()
    pool = await projection_pool(db, league, 9)
    await compute_projections(db, league, 9, now=BEFORE, player_ids=pool)
    await compute_rest_of_season(db, league, 9, pool)
    return world


async def test_waivers_rank_free_agents_for_my_lineup(
    db: AsyncSession, projected: dict[str, Any], client: httpx.AsyncClient
) -> None:
    league, team = projected["league"], projected["team"]
    resp = await client.get(
        f"/api/v1/leagues/{league.id}/waivers", headers=auth_headers(projected["user"].id)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["horizon"] == "ros" and body["ready"] is True
    assert body["horizon_weeks"] == list(range(9, 18)) and body["playoff_weeks"] == [15, 16, 17]
    # The fixture league is FAAB with a $100 budget.
    assert body["waiver_kind"] == "faab" and body["faab_budget"] == 100
    me = await db.get(Team, team.id)
    assert body["faab_remaining"] == 100 - (me.waiver_budget_used or 0)  # type: ignore[union-attr]
    assert body["my_waiver_position"] is None  # only shown for priority leagues

    rostered = set(
        await db.scalars(
            select(RosterEntry.player_id)
            .join(Team, Team.id == RosterEntry.team_id)
            .where(Team.league_id == league.id, RosterEntry.week == 9)
        )
    )
    players = body["players"]
    assert players, "the fixture's free agents should be listed"
    assert all(p["player"]["player_id"] not in rostered for p in players)
    gains = [p["gain"] for p in players]
    assert gains == sorted(gains, reverse=True)
    top = players[0]
    blue = await db.scalar(select(Player).where(Player.sleeper_id == BREAKOUT))
    assert top["player"]["player_id"] == blue.id  # type: ignore[union-attr]
    assert top["gain"] > 0 and top["gain_per_week"] > 0
    for p in players:
        assert p["status"] in ("free_agent", "waivers")
        if p["gain"] > 0:
            assert p["bid_low"] is not None and p["bid_low"] <= p["bid_high"]
            assert p["bid_high"] <= body["faab_remaining"]


async def test_this_week_horizon(projected: dict[str, Any], client: httpx.AsyncClient) -> None:
    league = projected["league"]
    resp = await client.get(
        f"/api/v1/leagues/{league.id}/waivers?horizon=week",
        headers=auth_headers(projected["user"].id),
    )
    assert resp.status_code == 200
    assert resp.json()["horizon_weeks"] == [9] and resp.json()["playoff_weeks"] == []


async def test_priority_league_with_a_claim_window(
    db: AsyncSession, projected: dict[str, Any]
) -> None:
    """The owner's usual format: rolling priority, 2-day claim window (ADR-046)."""
    league = projected["league"]
    await db.execute(
        update(League)
        .where(League.id == league.id)
        .values(waiver_rules={"kind": "rolling", "clear_days": 2, "min_bid": 0})
    )
    await db.commit()
    await db.refresh(league)
    membership = await db.scalar(
        select(LeagueMembership).where(LeagueMembership.league_id == league.id)
    )
    assert membership is not None
    # Jaydon Blue (fixture id 12457) was dropped on 2026-11-07 15:30 UTC.
    dropped = datetime(2026, 11, 7, 15, 30, tzinfo=UTC)
    view = await waivers_view(db, league, membership, "ros", now=dropped + timedelta(days=1))
    assert view.waiver_kind == "rolling" and view.faab_budget is None
    assert view.my_waiver_position is not None
    assert all(p.bid_low is None for p in view.players)
    blue = await db.scalar(select(Player).where(Player.sleeper_id == "12457"))
    assert blue is not None
    listed = next((p for p in view.players if p.player.player_id == blue.id), None)
    assert listed is not None, "the dropped player should be a candidate"
    assert listed.status == "waivers"
    assert listed.on_waivers_until == dropped + timedelta(days=2)

    later = await waivers_view(db, league, membership, "ros", now=dropped + timedelta(days=3))
    again = next(p for p in later.players if p.player.player_id == blue.id)
    assert again.status == "free_agent" and again.on_waivers_until is None


async def test_full_roster_suggests_a_drop(db: AsyncSession, projected: dict[str, Any]) -> None:
    league, team = projected["league"], projected["team"]
    membership = await db.scalar(
        select(LeagueMembership).where(LeagueMembership.league_id == league.id)
    )
    assert membership is not None
    # Shrink the bench so the roster is full: every add then needs a drop.
    count = len((await db.scalars(
        select(RosterEntry).where(RosterEntry.team_id == team.id, RosterEntry.week == 9,
                                  RosterEntry.slot.notin_(["IR", "TAXI"]))
    )).all())  # fmt: skip
    starters = [s for s in league.roster_slots if s != "BN"]
    league.roster_slots = starters + ["BN"] * (count - len(starters))
    await db.commit()
    view = await waivers_view(db, league, membership, "ros")
    useful = [p for p in view.players if p.gain > 0]
    assert useful and all(p.drop is not None for p in useful)


async def test_waivers_need_a_chosen_team_and_membership(
    db: AsyncSession, projected: dict[str, Any], client: httpx.AsyncClient
) -> None:
    league = projected["league"]
    stranger = await make_user(db, "stranger@example.com")
    resp = await client.get(
        f"/api/v1/leagues/{league.id}/waivers", headers=auth_headers(stranger.id)
    )
    assert resp.status_code == 404

    await db.execute(update(LeagueMembership).values(my_team_id=None))
    await db.commit()
    resp = await client.get(
        f"/api/v1/leagues/{league.id}/waivers", headers=auth_headers(projected["user"].id)
    )
    assert resp.status_code == 409 and resp.json()["code"] == "team_not_chosen"
