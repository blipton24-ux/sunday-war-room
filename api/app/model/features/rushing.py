"""Rushing-game features (P4 round 2, RB ideas approved 2026-11-13).

- Split rushing from receiving: the share of each game's points that came from catching the ball,
  so the two parts can be averaged with different memory lengths.
- Yards-per-carry luck: replace part of a game's rushing-yard points with what the league's
  typical yards per carry would have given for the same carries.
- Team carries: how many carries each team-game had, and how many a team is expected to get
  given the betting spread (favourites run more), fit on earlier seasons only.

All fits read seasons before the one being projected. Needs raw stat columns on the history frame.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

RECEIVING_POINTS = {"receptions": 0.5, "receiving_yards": 0.1, "receiving_tds": 6.0}
RUSHING_POINTS = {"rushing_yards": 0.1, "rushing_tds": 6.0}
RUSH_YARD_POINTS = 0.1  # every common scoring system gives 1 point per 10 rushing yards
MIN_CARRIES_TO_FIT = 500


def _weighted(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    total = pd.Series(0.0, index=df.index)
    for col, w in weights.items():
        total += w * df[col]
    return total


def receiving_share(df: pd.DataFrame) -> pd.Series:
    """Share of each game's points from receiving (reference weights); NaN for a game with
    neither rushing nor receiving production."""
    rec = _weighted(df, RECEIVING_POINTS).clip(lower=0.0)
    rush = _weighted(df, RUSHING_POINTS).clip(lower=0.0)
    total = rec + rush
    return rec / total.where(total > 0)


def fit_ypc(history: pd.DataFrame, before_season: int) -> dict[str, float]:
    """League yards per carry by position, from seasons before `before_season` only."""
    prior = history[history["season"] < before_season]
    out: dict[str, float] = {}
    for pos, g in prior.groupby("position"):
        carries = float(g["carries"].sum())
        if carries >= MIN_CARRIES_TO_FIT:
            out[str(pos)] = float(g["rushing_yards"].sum()) / carries
    return out


def regress_ypc(df: pd.DataFrame, ypc: dict[str, float], strength: float) -> pd.Series:
    """Points with `strength` (0..1) of the rushing yards above or below the league's typical
    yards per carry taken back out."""
    typical = df["position"].map(ypc)
    surplus = (df["rushing_yards"] - typical * df["carries"]).where(typical.notna(), 0.0)
    return df["points"] - strength * RUSH_YARD_POINTS * surplus


def team_carries(df: pd.DataFrame) -> pd.Series:
    """Each row's team carries in that game (every position's carries summed)."""
    return df.groupby(["team", "season", "week"])["carries"].transform("sum")


@dataclass(frozen=True)
class CarryFit:
    intercept: float  # team carries in a pick'em game
    per_point: float  # extra team carries per point of spread (positive: favoured)


def fit_carries_vs_spread(
    history: pd.DataFrame, games: dict[tuple[str, int, int], dict[str, Any]], before_season: int
) -> CarryFit | None:
    """Team carries against the betting spread, from seasons before `before_season` only."""
    prior = history[history["season"] < before_season]
    if prior.empty:
        return None
    per_game: pd.DataFrame = (
        prior.groupby(["team", "season", "week"])["carries"].sum().reset_index()
    )
    spread = [
        (games.get((str(t), int(s), int(w))) or {}).get("spread")
        for t, s, w in zip(per_game["team"], per_game["season"], per_game["week"], strict=True)
    ]
    per_game["spread"] = pd.to_numeric(pd.Series(spread, index=per_game.index), errors="coerce")
    usable = per_game.dropna(subset=["spread"])
    if len(usable) < 50:
        return None
    slope, intercept = np.polyfit(usable["spread"].to_numpy(), usable["carries"].to_numpy(), 1)
    return CarryFit(float(intercept), float(slope))
