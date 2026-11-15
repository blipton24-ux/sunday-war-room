"""Rushing-game signals: how much of a game's points came from receiving, and team carries.

Kept from the first P4 approach as a reference for P4 step 4: the signals here move into the
feature table (`app/model/ml/features.py`) and this file is deleted then.

Needs raw stat columns on the history frame.
"""

from __future__ import annotations

import pandas as pd

RECEIVING_POINTS = {"receptions": 0.5, "receiving_yards": 0.1, "receiving_tds": 6.0}
RUSHING_POINTS = {"rushing_yards": 0.1, "rushing_tds": 6.0}


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


def team_carries(df: pd.DataFrame) -> pd.Series:
    """Each row's team carries in that game (every position's carries summed)."""
    return df.groupby(["team", "season", "week"])["carries"].transform("sum")
