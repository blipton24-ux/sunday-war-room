"""An ESPN league through the real sync into Postgres (P3 steps 3-6, ADR-053).

Proves the whole path with synthetic ESPN responses: platform ids -> our players (direct id,
team defenses, name fallback), rosters, matchups with live player points, transactions, the
league's own scoring, and that a second sync changes nothing.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.espn import EspnAdapter, EspnHttp
from app.db.models import League, LeagueTransaction, Matchup, Player, RosterEntry, Team
from app.model.scoring import check_rules
from app.services.sync import refresh_live_matchups, sync_league
from tests import espn_fixtures as fx

pytestmark = pytest.mark.integration


@pytest.fixture
async def espn() -> AsyncIterator[EspnAdapter]:
    with fx.mock_espn():
        http = EspnHttp(retries=0)
        yield EspnAdapter(http, fx.SEASON)
        await http.aclose()


async def seed_players(db: AsyncSession) -> dict[str, Player]:
    """Our player list, as the Sleeper feed + nflverse would have left it."""
    players: dict[str, Player] = {}
    n = 0

    def add(key: str, **kw: object) -> None:
        nonlocal n
        n += 1
        p = Player(sleeper_id=f"S{n}", **kw)
        db.add(p)
        players[key] = p

    for i in range(4):
        o = i * 100
        add(
            f"qb{i}", name=f"Quarterback {i}", position="QB", nfl_team="KC", espn_id=str(fx.QB1 + o)
        )
        add(f"rb{i}", name=f"Runner {i}", position="RB", nfl_team="DEN", espn_id=str(fx.RB1 + o))
        add(
            f"rb2{i}",
            name=f"Backup Runner {i}",
            position="RB",
            nfl_team="DEN",
            espn_id=str(fx.RB2 + o),
        )
        add(f"wr{i}", name=f"Receiver {i}", position="WR", nfl_team="MIN", espn_id=str(fx.WR1 + o))
        add(f"te{i}", name=f"Tight End {i}", position="TE", nfl_team="NE", espn_id=str(fx.TE1 + o))
    add("k", name="Kicker", position="K", nfl_team="KC", espn_id=str(fx.K1))
    add("kc_def", name="Chiefs D/ST", position="DEF", nfl_team="KC", gsis_id="TEAM_KC")
    # the rookie ESPN knows by id 9000099, but our list has no espn_id for him yet
    add("rookie", name="Rookie Rusher", position="RB", nfl_team="LA")
    await db.commit()
    return players


async def count(db: AsyncSession, model: Any, *where: Any) -> int:
    return int(await db.scalar(select(func.count()).select_from(model).where(*where)) or 0)


async def run_sync(db: AsyncSession, espn: EspnAdapter) -> League:
    return await sync_league(db, espn, fx.PUBLIC_LEAGUE, current_week=9, history_weeks=[])


async def test_an_espn_league_syncs_into_the_database(db: AsyncSession, espn: EspnAdapter) -> None:
    players = await seed_players(db)
    league = await run_sync(db, espn)

    assert (league.platform, league.external_id, league.season) == ("espn", "424242", 2026)
    assert league.scoring_key and check_rules(league.scoring_rules).unsupported == {}
    assert league.waiver_rules["kind"] == "faab" and league.season_rules["playoff_week_start"] == 15
    assert league.roster_slots[:3] == ["QB", "RB", "RB"]

    teams = {
        t.external_id: t for t in await db.scalars(select(Team).where(Team.league_id == league.id))
    }
    assert set(teams) == {"1", "2", "3", "4"}
    assert teams["4"].name == "Gridiron Gang" and teams["1"].owner_external_id == fx.OWNER_GUIDS[0]

    rows = (await db.scalars(select(RosterEntry).where(RosterEntry.team_id == teams["1"].id))).all()
    by_player = {r.player_id: r for r in rows}
    assert by_player[players["qb0"].id].slot == "QB" and by_player[players["qb0"].id].is_starter
    assert by_player[players["rb20"].id].slot == "BN"
    assert by_player[players["kc_def"].id].slot == "DEF"  # ESPN's -16012 resolved to KC's defense
    assert by_player[players["rookie"].id].slot == "FLEX"  # matched by name + position + team


async def test_the_name_match_is_remembered_so_the_next_sync_needs_no_guess(
    db: AsyncSession, espn: EspnAdapter
) -> None:
    players = await seed_players(db)
    await run_sync(db, espn)
    await db.refresh(players["rookie"])
    assert players["rookie"].espn_id == str(fx.UNKNOWN_ROOKIE)


async def test_players_ESPN_has_but_we_cannot_name_are_skipped_not_invented(
    db: AsyncSession, espn: EspnAdapter
) -> None:
    await seed_players(db)
    league = await run_sync(db, espn)
    team1 = await db.scalar(
        select(Team).where(Team.league_id == league.id, Team.external_id == "1")
    )
    assert team1 is not None
    # 9 entries for team 1; the IDP linebacker has no row in our player list, so 8 are stored
    assert await count(db, RosterEntry, RosterEntry.team_id == team1.id) == 8


async def test_matchups_store_scores_and_the_bye(db: AsyncSession, espn: EspnAdapter) -> None:
    players = await seed_players(db)
    league = await run_sync(db, espn)
    teams = {
        t.external_id: t.id
        for t in await db.scalars(select(Team).where(Team.league_id == league.id))
    }
    matchups = (await db.scalars(select(Matchup).where(Matchup.league_id == league.id))).all()
    assert len(matchups) == 2  # team 1 v team 2, and team 3's bye
    versus = next(m for m in matchups if m.away_team_id is not None)
    assert {versus.home_team_id, versus.away_team_id} == {teams["1"], teams["2"]}
    bye = next(m for m in matchups if m.away_team_id is None)
    assert bye.home_team_id == teams["3"]
    home_points = (
        versus.home_player_points
        if versus.home_team_id == teams["1"]
        else versus.away_player_points
    )
    assert home_points[str(players["qb0"].id)] == 21.5


async def test_transactions_are_stored_with_espn_player_ids(
    db: AsyncSession, espn: EspnAdapter
) -> None:
    await seed_players(db)
    league = await run_sync(db, espn)
    txs = {
        t.external_id: t
        for t in await db.scalars(
            select(LeagueTransaction).where(LeagueTransaction.league_id == league.id)
        )
    }
    assert {"tx-fa", "tx-waiver", "tx-failed", "tx-trade"} <= set(txs)
    assert txs["tx-fa"].drops == {"222": "2"} and txs["tx-waiver"].waiver_bid == 12


async def test_syncing_twice_changes_nothing(db: AsyncSession, espn: EspnAdapter) -> None:
    await seed_players(db)
    league = await run_sync(db, espn)
    before = (
        await count(db, RosterEntry),
        await count(db, Matchup),
        await count(db, Team),
        await count(db, LeagueTransaction),
    )
    again = await run_sync(db, espn)
    assert again.id == league.id
    after = (
        await count(db, RosterEntry),
        await count(db, Matchup),
        await count(db, Team),
        await count(db, LeagueTransaction),
    )
    assert before == after


async def test_a_live_refresh_updates_player_points_through_the_espn_adapter(
    db: AsyncSession, espn: EspnAdapter
) -> None:
    players = await seed_players(db)
    league = await run_sync(db, espn)
    updated = await refresh_live_matchups(db, espn, league, 9)
    assert updated == 3  # three team rows in period 9 (two opponents and the bye)
    versus = await db.scalar(
        select(Matchup).where(Matchup.league_id == league.id, Matchup.away_team_id.is_not(None))
    )
    assert versus is not None
    all_points = {**versus.home_player_points, **versus.away_player_points}
    assert all_points[str(players["qb0"].id)] == 21.5
