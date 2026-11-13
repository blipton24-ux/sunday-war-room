"""Defense against each position, passing and rushing apart (P4 group B).

Today's opponent factor looks at fantasy points allowed to a position. These tables split what a
defense allows into the passing game (passing for quarterbacks, receiving for everyone else) and
the running game, and can also adjust for the quality of the offenses it has faced.

All tables are built from games before the week being projected (the caller passes `cur`).
Needs raw stat columns on the history frame.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

PASS_POINTS = {  # reference scoring, half PPR; receiving counts as the passing game
    "passing_yards": 0.04, "passing_tds": 4.0, "passing_interceptions": -1.0,
    "receptions": 0.5, "receiving_yards": 0.1, "receiving_tds": 6.0,
}  # fmt: skip
RUN_POINTS = {"rushing_yards": 0.1, "rushing_tds": 6.0}
DEFAULT_PASS_SHARE = {"QB": 0.85, "WR": 1.0, "TE": 1.0, "RB": 0.35}


def _weighted(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    total = pd.Series(0.0, index=df.index)
    for col, w in weights.items():
        total += w * df[col]
    return total


@dataclass(frozen=True)
class Allowed:
    """Per (defense, position): games, and points allowed per game in each part of the game."""

    games: dict[tuple[str, str], int]
    total: dict[tuple[str, str], float]
    passing: dict[tuple[str, str], float]
    running: dict[tuple[str, str], float]
    resid: dict[tuple[str, str], float]  # points above the players' own averages
    league_total: dict[str, float]
    league_passing: dict[str, float]
    league_running: dict[str, float]
    scale: dict[str, float]  # a typical player's points per game, to turn `resid` into a ratio


def build_allowed(cur: pd.DataFrame, positions: tuple[str, ...]) -> Allowed:
    """Tables from this season's games so far (`cur`, one row per player-game)."""
    skill = cur[cur["position"].isin(positions) & cur["opponent"].notna()].copy()
    skill["pass_pts"] = _weighted(skill, PASS_POINTS)
    skill["run_pts"] = _weighted(skill, RUN_POINTS)
    # points above the player's own season average: adjusts for who the defense has faced
    skill["resid"] = skill["points"] - skill.groupby("gsis_id")["points"].transform("mean")
    per_game = skill.groupby(["opponent", "position", "season", "week"], as_index=False)[
        ["points", "pass_pts", "run_pts", "resid"]
    ].sum()
    by = per_game.groupby(["opponent", "position"])
    mean = by[["points", "pass_pts", "run_pts", "resid"]].mean()
    count = by["points"].count()

    def league(col: str) -> dict[str, float]:
        return {str(k): float(v) for k, v in mean[col].groupby(level="position").mean().items()}

    scale = skill.groupby(["position", "gsis_id"])["points"].mean().groupby("position").mean()

    def keyed(values: pd.Series) -> dict[tuple[str, str], float]:
        index: list[Any] = values.index.tolist()
        return {(str(o), str(p)): float(v) for (o, p), v in zip(index, values, strict=True)}

    return Allowed(
        games={k: int(v) for k, v in keyed(count).items()},
        total=keyed(mean["points"]),
        passing=keyed(mean["pass_pts"]),
        running=keyed(mean["run_pts"]),
        resid=keyed(mean["resid"]),
        league_total=league("points"),
        league_passing=league("pass_pts"),
        league_running=league("run_pts"),
        scale={str(k): float(v) for k, v in scale.items()},
    )


def pass_share(player_games: pd.DataFrame | None, position: str) -> float:
    """Share of a player's own points that come from the passing game (default by position)."""
    default = DEFAULT_PASS_SHARE.get(position, 1.0)
    if player_games is None or len(player_games) < 3:
        return default
    passing = float(_weighted(player_games, PASS_POINTS).sum())
    running = float(_weighted(player_games, RUN_POINTS).sum())
    total = passing + running
    return passing / total if total > 0 else default


def ratio(
    table: dict[tuple[str, str], float], league: dict[str, float], key: tuple[str, str]
) -> float | None:
    """Points allowed relative to the league average for the position (None: no data)."""
    value, avg = table.get(key), league.get(key[1])
    if value is None or not avg or avg <= 0 or np.isnan(value):
        return None
    return value / avg
