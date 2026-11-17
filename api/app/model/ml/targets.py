"""What the P4 models predict (ADR-060): per position, volume counts and per-opportunity rates.

Volume targets use XGBoost's count mode (Poisson). Rate targets are a ratio of two stats in the
same game, learned with ordinary regression weighted by the denominator, so a game with one
target barely counts and a game with twelve counts twelve times as much.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

Kind = Literal["count", "rate"]


@dataclass(frozen=True)
class Target:
    name: str
    kind: Kind
    stat: str  # the count, or the rate's numerator
    per: str | None = None  # the rate's denominator (and weight)


ATTEMPTS = Target("attempts", "count", "attempts")
CARRIES = Target("carries", "count", "carries")
TARGETS = Target("targets", "count", "targets")
COMPLETION_RATE = Target("completion_rate", "rate", "completions", "attempts")
YARDS_PER_ATTEMPT = Target("yards_per_attempt", "rate", "passing_yards", "attempts")
PASS_TD_RATE = Target("pass_td_rate", "rate", "passing_tds", "attempts")
INT_RATE = Target("int_rate", "rate", "passing_interceptions", "attempts")
YARDS_PER_CARRY = Target("yards_per_carry", "rate", "rushing_yards", "carries")
RUSH_TD_RATE = Target("rush_td_rate", "rate", "rushing_tds", "carries")
CATCH_RATE = Target("catch_rate", "rate", "receptions", "targets")
YARDS_PER_CATCH = Target("yards_per_catch", "rate", "receiving_yards", "receptions")
REC_TD_RATE = Target("rec_td_rate", "rate", "receiving_tds", "targets")

BY_POSITION: dict[str, tuple[Target, ...]] = {
    "QB": (ATTEMPTS, CARRIES, COMPLETION_RATE, YARDS_PER_ATTEMPT, PASS_TD_RATE, INT_RATE,
           YARDS_PER_CARRY, RUSH_TD_RATE),
    "RB": (CARRIES, TARGETS, YARDS_PER_CARRY, RUSH_TD_RATE, CATCH_RATE, YARDS_PER_CATCH,
           REC_TD_RATE),
    "WR": (TARGETS, CARRIES, CATCH_RATE, YARDS_PER_CATCH, REC_TD_RATE, YARDS_PER_CARRY),
    "TE": (TARGETS, CARRIES, CATCH_RATE, YARDS_PER_CATCH, REC_TD_RATE, YARDS_PER_CARRY),
}  # fmt: skip


def label(stats: pd.DataFrame, target: Target) -> tuple[pd.Series, pd.Series]:
    """(value, weight) per row of `stats` (one row per player-game, raw stat columns).
    Counts weigh 1. A rate is NaN, weight 0, where the game had no opportunity."""

    def col(name: str) -> pd.Series:
        if name in stats.columns:
            return stats[name].fillna(0.0).astype(float)
        return pd.Series(0.0, index=stats.index)

    if target.kind == "count":
        return col(target.stat), pd.Series(1.0, index=stats.index)
    assert target.per is not None
    per = col(target.per)
    value = (col(target.stat) / per.where(per > 0)).astype(float)
    return value, per.where(per > 0, 0.0)


def naive(features: pd.DataFrame, target: Target) -> pd.Series:
    """The simple baseline every target is compared with: his own season-to-date value, else
    last season's, else the recent-games value (NaN with no history at all)."""
    if target.kind == "count":
        names = {"attempts": "attempts_pg", "carries": "carries_pg", "targets": "targets_pg"}
        base = names[target.name]
    else:
        base = target.name
    out = features[f"season_{base}"].copy()
    for window in ("last", "recent"):
        out = out.fillna(features[f"{window}_{base}"])
    return out.astype(float).where(lambda s: np.isfinite(s))
