"""Sleeper adapter against recorded (anonymized) responses from a real 2026 league.

No network: respx intercepts every request and serves tests/fixtures/sleeper/*.json.
"""

from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from app.adapters.base import (
    AdapterError,
    AdapterSchemaError,
    LeagueAdapter,
    NotFoundOnPlatform,
)
from app.adapters.sleeper import SleeperAdapter, build_roster
from tests.sleeper_fixtures import LEAGUE_ID, ME, fx, mock_sleeper


@pytest.fixture
async def sleeper() -> AsyncIterator[tuple[SleeperAdapter, respx.MockRouter]]:
    with mock_sleeper() as router:
        adapter = SleeperAdapter(retries=1)
        yield adapter, router
        await adapter.aclose()


def test_sleeper_satisfies_the_interface() -> None:
    adapter: LeagueAdapter = SleeperAdapter()  # mypy checks the Protocol here
    assert adapter.platform == "sleeper"


async def test_find_user_and_leagues(sleeper: tuple[SleeperAdapter, respx.MockRouter]) -> None:
    adapter, _ = sleeper
    user = await adapter.find_user("fixtureuser")
    assert user.external_user_id == ME
    leagues = await adapter.find_leagues(user, 2026)
    assert [(lg.external_id, lg.season, lg.total_teams) for lg in leagues] == [
        (LEAGUE_ID, 2026, 12)
    ]


async def test_unknown_username(sleeper: tuple[SleeperAdapter, respx.MockRouter]) -> None:
    adapter, _ = sleeper
    with pytest.raises(NotFoundOnPlatform):
        await adapter.find_user("nobody")


async def test_league_settings(sleeper: tuple[SleeperAdapter, respx.MockRouter]) -> None:
    adapter, _ = sleeper
    league = await adapter.fetch_league(LEAGUE_ID)
    assert league.ref.name == "Fixture League"
    assert league.status == "in_season"
    assert league.scoring_rules["rec"] == 0.5  # half PPR
    assert league.scoring_rules["pass_td"] == 4.0
    assert league.roster_slots[:3] == ["QB", "RB", "RB"]
    assert league.roster_slots.count("FLEX") == 2


async def test_teams_have_names_records_and_slotted_rosters(
    sleeper: tuple[SleeperAdapter, respx.MockRouter],
) -> None:
    adapter, _ = sleeper
    league = await adapter.fetch_league(LEAGUE_ID)
    teams = await adapter.fetch_teams(league)
    assert len(teams) == 12
    mine = next(t for t in teams if t.owner_external_id == ME)
    assert mine.name == "Team 1"
    assert mine.wins + mine.losses + mine.ties > 0

    n_starting_slots = sum(1 for s in league.roster_slots if s != "BN")
    for team in teams:
        starters = [s for s in team.roster if s.is_starter]
        assert len(starters) <= n_starting_slots
        ids = [s.player_external_id for s in team.roster]
        assert len(ids) == len(set(ids)), "a player appears twice on one roster"
        # Every QB slot holds a QB, etc. (positions come from the players fixture)
    players = {p["player_id"]: p for p in fx("players").values()}
    for spot in mine.roster:
        if spot.slot in {"QB", "RB", "WR", "TE", "DEF"}:
            assert players[spot.player_external_id]["position"] == spot.slot


async def test_matchups_pair_teams(sleeper: tuple[SleeperAdapter, respx.MockRouter]) -> None:
    adapter, _ = sleeper
    league = await adapter.fetch_league(LEAGUE_ID)
    rows = await adapter.fetch_matchups(league, 8)
    assert len(rows) == 12
    keys = [r.matchup_key for r in rows if r.matchup_key]
    assert all(keys.count(k) == 2 for k in keys), "each matchup has exactly two teams"
    assert all(r.points is not None and r.points > 0 for r in rows)


async def test_players_crosswalk(sleeper: tuple[SleeperAdapter, respx.MockRouter]) -> None:
    adapter, _ = sleeper
    players = await adapter.fetch_players()
    assert len(players) > 250
    # Sleeper's gsis_id is sparse (recorded: 58 of 315), so the real crosswalk comes from
    # nflverse. Here we only check ids are normalized: never "" and always strings.
    assert all(p.gsis_id is None or p.gsis_id.startswith("00-") for p in players)
    assert any(p.gsis_id for p in players)
    defense = [p for p in players if p.position == "DEF"]
    assert defense and all(p.gsis_id is None for p in defense)


async def test_state(sleeper: tuple[SleeperAdapter, respx.MockRouter]) -> None:
    adapter, _ = sleeper
    state = await adapter.fetch_state()
    assert (state.season, state.week, state.season_type) == (2026, 9, "regular")


async def test_shape_change_fails_loudly(sleeper: tuple[SleeperAdapter, respx.MockRouter]) -> None:
    adapter, router = sleeper
    broken = fx("league")
    del broken["scoring_settings"]
    router.get(f"/league/{LEAGUE_ID}").respond(json=broken)
    with pytest.raises(AdapterSchemaError, match="scoring_settings"):
        await adapter.fetch_league(LEAGUE_ID)


async def test_retries_then_gives_up(sleeper: tuple[SleeperAdapter, respx.MockRouter]) -> None:
    adapter, router = sleeper
    route = router.get("/state/nfl").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json=fx("state"))]
    )
    assert (await adapter.fetch_state()).week == 9
    assert route.call_count == 2

    router.get("/state/nfl").respond(503)
    with pytest.raises(AdapterError, match="503"):
        await adapter.fetch_state()


def test_build_roster_handles_empty_slots_ir_and_taxi() -> None:
    slots = ["QB", "RB", "FLEX", "BN", "BN", "IR"]
    spots = build_roster(slots, ["1", "0", "3"], ["1", "3", "4", "5", "6"], ["5"], ["6"])
    assert [(s.player_external_id, s.slot, s.is_starter) for s in spots] == [
        ("1", "QB", True),
        ("3", "FLEX", True),  # the RB slot was empty ("0")
        ("5", "IR", False),
        ("6", "TAXI", False),
        ("4", "BN", False),
    ]


def test_build_roster_rejects_more_starters_than_slots() -> None:
    with pytest.raises(AdapterSchemaError):
        build_roster(["QB", "BN"], ["1", "2"], ["1", "2"], None, None)


def test_two_way_player_gets_his_fantasy_position() -> None:
    from app.adapters.sleeper import fantasy_position

    assert fantasy_position("DB", ["DB", "WR"]) == "WR"  # recorded: Travis Hunter
    assert fantasy_position("QB", ["QB"]) == "QB"
    assert fantasy_position("LB", ["LB"]) is None
