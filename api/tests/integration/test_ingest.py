"""nflverse ingest into Postgres: idempotent per season, crosswalk links Sleeper players."""

from datetime import UTC, datetime

import polars as pl
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InjuryReport, NflGame, Player, PlayerWeekStats
from app.services import ingest
from app.services.ingest import NflverseFrames

pytestmark = pytest.mark.integration


def frames(receiving_yards: float = 80.0) -> NflverseFrames:
    schedule = pl.DataFrame(
        {
            "game_id": ["2026_01_KC_LA"],
            "season": [2026],
            "week": [1],
            "game_type": ["REG"],
            "home": ["LA"],
            "away": ["KC"],
            "kickoff_at": [datetime(2026, 9, 13, 20, 25, tzinfo=UTC)],
            "home_score": [24],
            "away_score": [17],
        }
    )
    key = {"season": 2026, "week": 1, "season_type": "REG"}
    player_stats = pl.DataFrame(
        [
            key | {"gsis_id": "00-1", "name": "Puka", "position": "WR", "team": "LA",
                   "opponent": "KC", "receptions": 7.0, "receiving_yards": receiving_yards,
                   "rushing_yards": 0.0},
        ]
    )  # fmt: skip
    defense = pl.DataFrame(
        [key | {"gsis_id": "TEAM_LA", "name": "LA", "position": "DEF", "team": "LA",
                "opponent": "KC", "def_sacks": 3.0, "points_allowed": 17.0}]
    )  # fmt: skip
    snaps = pl.DataFrame({"gsis_id": ["00-1"], "season": [2026], "week": [1], "offense_pct": [0.9]})
    ids = pl.DataFrame({"gsis_id": ["00-1"], "sleeper_id": ["9001"], "espn_id": ["4426515"]})
    injuries = pl.DataFrame(
        {
            "gsis_id": ["00-1"],
            "season": [2026],
            "week": [1],
            "report_status": ["Questionable"],
            "roster_status": ["RES"],
            "practice_status": ["Limited"],
            "injury": [
                "Hamstring, Ankle, Knee, Shoulder, Concussion, Illness, Back, Foot, Calf, Groin"
            ],
        }
    )
    return NflverseFrames(schedule, player_stats, defense, snaps, ids, injuries)


async def test_ingest_is_idempotent_and_links_players(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    db.add_all(
        [
            Player(sleeper_id="9001", name="Puka Nacua", position="WR", nfl_team="LA"),
            Player(sleeper_id="LAR", name="Rams", position="DEF", nfl_team="LA"),
            Player(sleeper_id="7777", name="No nflverse id", position="WR"),
        ]
    )
    await db.commit()

    monkeypatch.setattr(ingest, "fetch_frames", lambda seasons: frames(80.0))
    first = await ingest.ingest_nflverse(db, [2026])
    monkeypatch.setattr(ingest, "fetch_frames", lambda seasons: frames(95.0))  # stat correction
    second = await ingest.ingest_nflverse(db, [2026])

    assert first["player_weeks"] == second["player_weeks"] == 2
    assert await db.scalar(select(func.count()).select_from(PlayerWeekStats)) == 2
    assert await db.scalar(select(func.count()).select_from(NflGame)) == 1

    wr = await db.get(PlayerWeekStats, ("00-1", 2026, 1))
    assert wr is not None
    assert wr.stats["receiving_yards"] == 95.0  # the re-run replaced, not duplicated
    assert "rushing_yards" not in wr.stats  # zeros are omitted
    assert wr.offense_snap_pct == 0.9

    links = dict((await db.execute(select(Player.sleeper_id, Player.gsis_id))).all())
    assert links == {"9001": "00-1", "LAR": "TEAM_LA", "7777": None}
    espn = dict((await db.execute(select(Player.sleeper_id, Player.espn_id))).all())
    assert espn["9001"] == "4426515"  # filled for headshots
    assert second["players_linked"] == 0  # nothing changed the second time
    assert first["injury_reports"] == second["injury_reports"] == 1  # replaced, not duplicated
    injury = await db.get(InjuryReport, ("00-1", 2026, 1))
    assert injury is not None and injury.report_status == "Questionable"
    assert injury.roster_status == "RES" and len(injury.injury or "") > 64  # long text fits


async def test_crosswalk_moves_an_id_without_tripping_uniqueness(db: AsyncSession) -> None:
    """If nflverse fixes a mapping, the gsis id moves to the right Sleeper player."""
    db.add_all(
        [
            Player(sleeper_id="1", name="Wrongly linked", position="WR", gsis_id="00-9"),
            Player(sleeper_id="2", name="Right player", position="WR"),
        ]
    )
    await db.commit()
    changed = await ingest.apply_crosswalk(
        db, pl.DataFrame({"gsis_id": ["00-9"], "sleeper_id": ["2"]})
    )
    await db.commit()
    assert changed == 1
    links = dict((await db.execute(select(Player.sleeper_id, Player.gsis_id))).all())
    assert links == {"1": None, "2": "00-9"}
