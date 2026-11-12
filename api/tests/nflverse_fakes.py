"""Tiny stand-ins for nflverse files, shaped like the real ones (all contract columns present).

Tests patch `nflreadpy.load_*` with these, so nothing is downloaded.
"""

from typing import Any

import polars as pl

from app.sources.nflverse import (
    PLAYER_KEY_COLUMNS,
    PLAYER_STAT_COLUMNS,
    SCHEDULE_COLUMNS,
    TEAM_DEF_COLUMNS,
    TEAM_KEY_COLUMNS,
)


def player_stats(rows: list[dict[str, Any]]) -> pl.DataFrame:
    base = {c: 0.0 for c in PLAYER_STAT_COLUMNS} | {
        "player_display_name": "X",
        "season_type": "REG",
        "opponent_team": "KC",
    }
    out = [base | {"player_id": r.get("gsis_id")} | r for r in rows]
    df = pl.DataFrame(out)
    return df.drop([c for c in ("gsis_id",) if c in df.columns])


def team_stats(rows: list[dict[str, Any]]) -> pl.DataFrame:
    base = {c: 0.0 for c in TEAM_DEF_COLUMNS} | {"season_type": "REG"}
    df = pl.DataFrame([base | r for r in rows])
    assert set(TEAM_KEY_COLUMNS) <= set(df.columns)
    return df


def schedules(rows: list[dict[str, Any]]) -> pl.DataFrame:
    base = {"game_type": "REG", "gameday": "2026-09-13", "gametime": "13:00"}
    df = pl.DataFrame([base | r for r in rows])
    assert set(SCHEDULE_COLUMNS) <= set(df.columns)
    return df


def snap_counts(rows: list[dict[str, Any]]) -> pl.DataFrame:
    return pl.DataFrame([{"game_type": "REG"} | r for r in rows])


def injuries(rows: list[dict[str, Any]]) -> pl.DataFrame:
    """Raw nflverse injury rows: one per practice day, so a player-week can have several."""
    base = {
        "game_type": "REG", "report_status": None, "practice_status": None,
        "report_primary_injury": None, "date_modified": "2026-09-10T00:00:00Z",
    }  # fmt: skip
    return pl.DataFrame(
        [base | r for r in rows],
        schema_overrides={
            "report_status": pl.String,
            "practice_status": pl.String,
            "report_primary_injury": pl.String,
        },
    )


def rosters_weekly(rows: list[dict[str, Any]]) -> pl.DataFrame:
    return pl.DataFrame([{"game_type": "REG", "status": "ACT"} | r for r in rows])


def ff_playerids(rows: list[dict[str, Any]]) -> pl.DataFrame:
    base = {"espn_id": None, "yahoo_id": None, "pfr_id": None, "name": "X", "position": "WR"}
    return pl.DataFrame([base | r for r in rows], schema_overrides={"sleeper_id": pl.Int64})


assert PLAYER_KEY_COLUMNS  # imported for documentation: fakes must carry these columns
