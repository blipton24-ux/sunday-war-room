"""Builds the world the end-to-end browser tests run in (docker-compose.e2e.yml runs this once).

    python -m tests.e2e_seed

It loads the recorded Sleeper league through the real adapter (pointed at the local stand-in
server), then invents the NFL side: games, stat lines and projections, shaped so that every
screen state the UI has appears for the fixture user's team ("Team 1"):

    QB, RB1, RB2, FLEX1   game FINISHED       (the QB has a huge game: "Boom")
    WR1                   game IN PROGRESS    (locked)
    WR2                   game upcoming
    TE                    game upcoming, listed QUESTIONABLE
    FLEX2                 team on BYE
    DEF                   game upcoming
    one bench WR          game upcoming, far better than WR2 -> a swap to make

and for the P2 screens: the league's free agents have stat lines too (Jaydon Blue is a breakout
RB, the top waiver add), and weeks 10-17 are scheduled, so rest-of-season values exist.

Times are relative to "now", so the seeded world stays valid whenever the tests run. Past weeks
carry graded, pre-kickoff projections, so the Accuracy screen has real numbers.
"""

from __future__ import annotations

import asyncio
import zlib
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.sleeper import SleeperAdapter
from app.db.models import League, NflGame, Player, PlayerWeekStats, RosterEntry, Team
from app.db.session import get_engine, get_sessionmaker
from app.nfl_teams import NFL_TEAMS, defense_key
from app.services.grading import grade_finished
from app.services.projections import (
    compute_projections,
    compute_rest_of_season,
    projection_pool,
)
from app.services.sync import sync_league, upsert_platform_players
from tests.sleeper_fixtures import LEAGUE_ID, ME

SEASON, WEEK = 2026, 9
LAST_WEEK = 17
BREAKOUT = "12457"  # Jaydon Blue, a free agent in the fixture league

BASE_LINE: dict[str, dict[str, float]] = {
    "QB": {"completions": 21, "attempts": 33, "passing_yards": 245, "passing_tds": 1.6,
           "passing_interceptions": 0.6, "rushing_yards": 14},
    "RB": {"carries": 14, "rushing_yards": 62, "rushing_tds": 0.4, "receptions": 2.6,
           "receiving_yards": 20, "targets": 3.4},
    "WR": {"receptions": 5, "targets": 7.5, "receiving_yards": 66, "receiving_tds": 0.4},
    "TE": {"receptions": 4, "targets": 5.5, "receiving_yards": 44, "receiving_tds": 0.3},
    "K": {"fg_made": 1.7, "fg_att": 2, "fg_made_30_39": 0.8, "fg_made_40_49": 0.6,
          "pat_made": 2.2, "pat_att": 2.3},
    "DEF": {"points_allowed": 21, "def_sacks": 2.2, "def_interceptions": 0.8,
            "fumble_recovery_opp": 0.5},
}  # fmt: skip

# Scenario for "Team 1": starter slot index -> status of that player's NFL team.
SCENARIO = ["final", "final", "final", "live", "upcoming", "upcoming", "final", "bye", "upcoming"]
Status = str  # final / live / upcoming / bye


def wiggle(key: str) -> float:
    """A repeatable 0.7-1.3 factor: same player and week always give the same stat line."""
    return 0.7 + 0.6 * (zlib.crc32(key.encode()) % 1000) / 1000


def stat_line(gsis_id: str, position: str, week: int, mult: float = 1.0) -> dict[str, float]:
    factor = wiggle(f"{gsis_id}:{week}") * mult
    return {k: round(v * factor, 2) for k, v in BASE_LINE[position].items()}


def team_statuses(my_starters: list[Player]) -> dict[str, Status]:
    """Every NFL team's status this week, with the scenario teams fixed first."""
    status: dict[str, Status] = {}
    protected: set[str] = set()
    for player, wanted in zip(my_starters, SCENARIO, strict=False):
        if player.nfl_team and player.nfl_team not in status:
            status[player.nfl_team] = wanted
            protected.add(player.nfl_team)
    cycle = ["upcoming", "final", "upcoming", "live"]
    for i, team in enumerate(sorted(NFL_TEAMS - status.keys())):
        status[team] = cycle[i % len(cycle)]
    for group in ("final", "live", "upcoming"):  # games need pairs: fix any odd group
        members = [t for t in sorted(status) if status[t] == group]
        if len(members) % 2:
            movable = [t for t in members if t not in protected]
            status[movable[-1]] = "bye"
    return status


def games_for(status: dict[str, Status], week: int, now: datetime) -> list[NflGame]:
    games = []
    when = {"final": now - timedelta(hours=30), "live": now - timedelta(hours=1),
            "upcoming": now + timedelta(hours=30)}  # fmt: skip
    for group in ("final", "live", "upcoming"):
        teams = [t for t in sorted(status) if status[t] == group]
        for i in range(0, len(teams) - 1, 2):
            home, away = teams[i], teams[i + 1]
            done = group == "final"
            games.append(
                NflGame(game_id=f"e2e_{SEASON}_{week:02d}_{away}_{home}", season=SEASON, week=week,
                        game_type="REG", home=home, away=away, kickoff_at=when[group],
                        home_score=24 if done else None, away_score=17 if done else None)
            )  # fmt: skip
    return games


def future_week_games(week: int, now: datetime) -> list[NflGame]:
    """Weeks after the current one, everyone playing, rotating opponents."""
    teams = sorted(NFL_TEAMS)
    shift = week % (len(teams) - 1) + 1
    order = teams[:1] + teams[1:][shift:] + teams[1:][:shift]
    kickoff = now + timedelta(days=(week - WEEK) * 7)
    return [
        NflGame(game_id=f"e2e_{SEASON}_{week:02d}_{order[i + 1]}_{order[i]}", season=SEASON,
                week=week, game_type="REG", home=order[i], away=order[i + 1], kickoff_at=kickoff)
        for i in range(0, len(order), 2)
    ]  # fmt: skip


def past_week_games(week: int, now: datetime) -> list[NflGame]:
    teams = sorted(NFL_TEAMS)
    kickoff = now - timedelta(days=(WEEK - week) * 7 + 1)
    return [
        NflGame(game_id=f"e2e_{SEASON}_{week:02d}_{teams[i + 1]}_{teams[i]}", season=SEASON,
                week=week, game_type="REG", home=teams[i], away=teams[i + 1],
                kickoff_at=kickoff, home_score=21, away_score=20)
        for i in range(0, len(teams), 2)
    ]  # fmt: skip


async def my_roster(db: AsyncSession, league: League) -> tuple[list[Player], list[Player]]:
    """(starters in lineup order, bench) for the fixture user's team in the current week."""
    team = await db.scalar(
        select(Team).where(Team.league_id == league.id, Team.owner_external_id == ME)
    )
    assert team is not None, "fixture user's team not found"
    entries = (
        await db.scalars(
            select(RosterEntry).where(RosterEntry.team_id == team.id, RosterEntry.week == WEEK)
        )
    ).all()
    order = {s: i for i, s in enumerate(dict.fromkeys(league.roster_slots))}
    starters = sorted((e for e in entries if e.is_starter), key=lambda e: (order[e.slot], e.id))
    by_id = {p.id: p for p in await db.scalars(select(Player))}
    return (
        [by_id[e.player_id] for e in starters],
        [by_id[e.player_id] for e in entries if not e.is_starter],
    )


async def seed() -> dict[str, Any]:
    now = datetime.now(UTC).replace(microsecond=0)
    adapter = SleeperAdapter()
    async with get_sessionmaker()() as db:
        await upsert_platform_players(db, "sleeper", await adapter.fetch_players())
        players = list((await db.scalars(select(Player))).all())
        await db.execute(
            update(Player),
            [
                {"id": p.id, "gsis_id": defense_key(p.sleeper_id or "")
                 if p.position == "DEF" else f"E2E-{p.sleeper_id}"}
                for p in players
            ],
        )  # fmt: skip
        await db.commit()

        league = await sync_league(db, adapter, LEAGUE_ID, current_week=WEEK,
                                   history_weeks=range(1, WEEK))  # fmt: skip
        starters, bench = await my_roster(db, league)
        status = team_statuses(starters)

        # The bench player to swap in: a WR on an upcoming team, far stronger than the others.
        swap_in = next(
            p for p in bench if p.position == "WR" and status.get(p.nfl_team or "") == "upcoming"
        )
        te = next(p for p in starters if p.position == "TE")
        qb = next(p for p in starters if p.position == "QB")
        assert status[te.nfl_team or ""] == "upcoming", "the TE's game must be upcoming"
        assert "bye" in {status.get(p.nfl_team or "") for p in starters}, "no starter on bye"
        assert "live" in {status.get(p.nfl_team or "") for p in starters}, "no starter in progress"
        await db.execute(
            update(Player).where(Player.id == te.id).values(injury_status="Questionable")
        )

        future = range(WEEK + 1, LAST_WEEK + 1)
        db.add_all([*games_for(status, WEEK, now),
                    *[g for w in range(1, WEEK) for g in past_week_games(w, now)],
                    *[g for w in future for g in future_week_games(w, now)]])  # fmt: skip

        rostered = {
            pid
            for (pid,) in (
                await db.execute(select(RosterEntry.player_id).where(RosterEntry.week == WEEK))
            )
        }
        rows: list[PlayerWeekStats] = []
        for p in players:
            if p.position not in BASE_LINE or not p.gsis_id or not p.nfl_team:
                continue
            free_agent = p.id not in rostered
            for week in range(1, WEEK + 1):
                if week == WEEK and status.get(p.nfl_team or "") != "final":
                    continue  # no result yet for games that haven't finished
                mult = 3.0 if p.id == swap_in.id and week < WEEK else 1.0
                if free_agent:
                    mult = 2.2 if p.sleeper_id == BREAKOUT else 0.6
                if week == WEEK and p.id == qb.id:
                    mult = 3.0  # the Boom: far above his projected range
                rows.append(PlayerWeekStats(
                    gsis_id=p.gsis_id, season=SEASON, week=week, season_type="REG",
                    position=p.position, team=p.nfl_team, opponent="XX",
                    stats=stat_line(p.gsis_id, p.position, week, mult), offense_snap_pct=0.75,
                ))  # fmt: skip
        db.add_all(rows)
        await db.commit()

        # Projections as the app would have made them: before kickoff, then frozen at kickoff.
        await compute_projections(db, league, WEEK - 1, now=now - timedelta(days=9))
        await compute_projections(db, league, WEEK, now=now - timedelta(hours=60))
        await compute_projections(db, league, WEEK - 1, now=now)
        await compute_projections(db, league, WEEK, now=now)
        graded = await grade_finished(db, SEASON)
        # P2: free agents and rest of season, as the sync job computes them.
        pool = await projection_pool(db, league, WEEK)
        await compute_projections(db, league, WEEK, now=now, player_ids=pool)
        await compute_rest_of_season(db, league, WEEK, pool, now=now)

        summary = {
            "teams": {s: sorted(t for t in status if status[t] == s) for s in
                      ("final", "live", "upcoming", "bye")},
            "swap_in": swap_in.name,
            "questionable": te.name,
            "boom": qb.name,
            "graded": graded,
        }  # fmt: skip
    await adapter.aclose()
    await get_engine().dispose()
    return summary


if __name__ == "__main__":
    result = asyncio.run(seed())
    print(f"e2e seed done: {result}", flush=True)
