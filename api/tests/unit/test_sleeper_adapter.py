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
from app.adapters.sleeper import (
    SleeperAdapter,
    _LeagueSettings,
    build_roster,
    season_rules,
    waiver_rules,
)
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


async def test_league_rules_faab_dynasty(sleeper: tuple[SleeperAdapter, respx.MockRouter]) -> None:
    """ADR-046: the fixture league is a FAAB, dynasty league with daily waivers."""
    adapter, _ = sleeper
    league = await adapter.fetch_league(LEAGUE_ID)
    w = league.waivers
    assert (w.kind, w.budget, w.min_bid, w.clear_days, w.daily) == ("faab", 100, 1, 0, True)
    assert w.daily_hour == 9
    assert w.raw["waiver_type"] == 2  # raw values kept for later checks
    r = league.season_rules
    assert (r.kind, r.start_week, r.playoff_week_start) == ("dynasty", 1, 15)
    assert (r.trade_deadline, r.trades_allowed) == (10, True)


@pytest.mark.parametrize(
    ("settings", "kind", "budget"),
    [
        ({"waiver_type": 0, "waiver_budget": 100}, "rolling", None),  # budget ignored
        ({"waiver_type": 1}, "reverse_standings", None),
        ({"waiver_type": 2, "waiver_budget": 200}, "faab", 200),
        ({}, "rolling", None),  # Sleeper's default when the setting is absent
        ({"waiver_type": 7}, "rolling", None),  # unknown code: safe default, raw kept
    ],
)
def test_waiver_kinds(settings: dict[str, int], kind: str, budget: int | None) -> None:
    w = waiver_rules(_LeagueSettings(**settings))
    assert (w.kind, w.budget) == (kind, budget)
    assert w.raw.get("waiver_type") == settings.get("waiver_type")


def test_priority_league_with_a_claim_window() -> None:
    """The owner's usual format: priority waivers for a couple of days, then free agency."""
    w = waiver_rules(_LeagueSettings(waiver_type=0, waiver_clear_days=2, waiver_day_of_week=2))
    assert (w.kind, w.clear_days, w.weekly_day, w.daily, w.daily_hour) == (
        "rolling",
        2,
        2,
        False,
        None,
    )


def test_season_rules_defaults_and_no_deadline() -> None:
    r = season_rules(_LeagueSettings())
    assert (r.kind, r.start_week, r.playoff_week_start, r.trade_deadline) == (
        "redraft",
        1,
        None,
        None,
    )
    assert season_rules(_LeagueSettings(trade_deadline=99, type=1)).trade_deadline is None
    assert season_rules(_LeagueSettings(type=1, disable_trades=1)).trades_allowed is False


async def test_teams_carry_waiver_position_and_faab_spent(
    sleeper: tuple[SleeperAdapter, respx.MockRouter],
) -> None:
    adapter, _ = sleeper
    teams = await adapter.fetch_teams(await adapter.fetch_league(LEAGUE_ID))
    positions = sorted(t.waiver_position for t in teams if t.waiver_position is not None)
    assert positions == list(range(1, 13))
    mine = next(t for t in teams if t.owner_external_id == ME)
    assert mine.waiver_budget_used is not None and mine.waiver_budget_used >= 0


async def test_matchups_carry_points_per_player(
    sleeper: tuple[SleeperAdapter, respx.MockRouter],
) -> None:
    adapter, _ = sleeper
    rows = await adapter.fetch_matchups(await adapter.fetch_league(LEAGUE_ID), 8)
    for r in rows:
        starters = [s.player_external_id for s in r.roster if s.is_starter]
        assert r.points is not None
        starter_total = sum(r.player_points.get(pid, 0.0) for pid in starters)
        assert starter_total == pytest.approx(r.points, abs=0.05)


async def test_transactions(sleeper: tuple[SleeperAdapter, respx.MockRouter]) -> None:
    adapter, _ = sleeper
    league = await adapter.fetch_league(LEAGUE_ID)
    week8 = await adapter.fetch_transactions(league, 8)
    claim = next(t for t in week8 if t.status == "complete")
    assert (claim.kind, claim.week, claim.waiver_bid) == ("waiver", 8, 7)
    assert claim.adds == {"11630": "3"} and claim.drops == {"4981": "3"}
    assert claim.created_at.tzinfo is not None
    assert [t.status for t in week8] == ["complete", "failed"]

    week9 = await adapter.fetch_transactions(league, 9)
    assert {t.kind for t in week9} == {"free_agent", "trade"}
    assert await adapter.fetch_transactions(league, 3) == []


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
