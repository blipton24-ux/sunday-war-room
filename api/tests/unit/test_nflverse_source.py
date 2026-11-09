"""The nflverse source module: contracts fail loudly, data comes out clean and canonical."""

from datetime import UTC, datetime

import nflreadpy
import polars as pl
import pytest

from app.sources import nflverse
from tests import nflverse_fakes as fake


def test_missing_stat_column_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    df = fake.player_stats(
        [{"gsis_id": "00-1", "position": "WR", "season": 2026, "week": 1, "team": "KC"}]
    ).drop("receiving_yards")
    monkeypatch.setattr(nflreadpy, "load_player_stats", lambda seasons: df)
    with pytest.raises(nflverse.NflverseSchemaError, match="receiving_yards"):
        nflverse.load_player_stats([2026])


def test_missing_season_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never quietly train on fewer seasons than asked for."""
    df = fake.player_stats(
        [{"gsis_id": "00-1", "position": "WR", "season": 2025, "week": 1, "team": "KC"}]
    )
    monkeypatch.setattr(nflreadpy, "load_player_stats", lambda seasons: df)
    with pytest.raises(nflverse.NflverseSchemaError, match=r"\[2026\]"):
        nflverse.load_player_stats([2025, 2026])


def test_player_stats_keep_regular_season_fantasy_players(monkeypatch: pytest.MonkeyPatch) -> None:
    df = fake.player_stats(
        [
            {"gsis_id": "00-1", "position": "WR", "season": 2026, "week": 1, "team": "LA",
             "opponent_team": "LAR", "receiving_yards": 88.0},
            {"gsis_id": "00-2", "position": "CB", "season": 2026, "week": 1, "team": "KC"},
            {"gsis_id": "00-3", "position": "QB", "season": 2026, "week": 19, "team": "KC",
             "season_type": "POST"},
            {"gsis_id": None, "position": "RB", "season": 2026, "week": 1, "team": "KC"},
        ]
    )  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_player_stats", lambda seasons: df)
    out = nflverse.load_player_stats([2026])
    assert out["gsis_id"].to_list() == ["00-1"]
    assert out["team"].to_list() == ["LA"] and out["opponent"].to_list() == ["LA"]
    assert out["receiving_yards"].to_list() == [88.0]


def test_schedule_kickoff_is_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    df = fake.schedules(
        [{"game_id": "2026_01_KC_LAR", "season": 2026, "week": 1, "home_team": "LAR",
          "away_team": "KC", "home_score": None, "away_score": None,
          "gameday": "2026-09-13", "gametime": "16:25"}]
    )  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_schedules", lambda seasons: df)
    out = nflverse.load_schedule([2026]).row(0, named=True)
    assert out["home"] == "LA"
    # 4:25 PM Eastern (daylight time) = 20:25 UTC
    assert out["kickoff_at"] == datetime(2026, 9, 13, 20, 25, tzinfo=UTC)


def test_defense_rows_get_points_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    sched = pl.DataFrame(
        {"season": [2026], "week": [1], "home": ["LA"], "away": ["KC"],
         "home_score": [24], "away_score": [17]}
    )  # fmt: skip
    ts = fake.team_stats(
        [{"team": "LA", "opponent_team": "KC", "season": 2026, "week": 1, "def_sacks": 3.0},
         {"team": "KC", "opponent_team": "LA", "season": 2026, "week": 1}]
    )  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_team_stats", lambda seasons: ts)
    out = {r["gsis_id"]: r for r in nflverse.load_defense_stats([2026], sched).to_dicts()}
    assert out["TEAM_LA"]["points_allowed"] == 17.0 and out["TEAM_LA"]["def_sacks"] == 3.0
    assert out["TEAM_KC"]["points_allowed"] == 24.0
    assert out["TEAM_KC"]["position"] == "DEF"


def test_crosswalk_drops_ambiguous_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    ids = fake.ff_playerids(
        [
            {"gsis_id": "00-1", "sleeper_id": 100},
            {"gsis_id": "00-2", "sleeper_id": 200},
            {"gsis_id": "00-3", "sleeper_id": 200},  # sleeper 200 maps to two players
            {"gsis_id": None, "sleeper_id": 300},
        ]
    )
    monkeypatch.setattr(nflreadpy, "load_ff_playerids", lambda: ids)
    out = nflverse.load_id_crosswalk()
    assert out.select("gsis_id", "sleeper_id").rows() == [("00-1", "100")]
