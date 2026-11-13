"""Opportunity features (P4 group A): what a player was given, apart from what he did with it.

Expected points: a position's fantasy points are regressed on its opportunities (targets and
carries; pass attempts and carries for quarterbacks) using earlier seasons only, so a game's
expected points measure volume at league-average efficiency. Touchdown regression: touchdowns
are lucky, so a game's actual touchdown points are partly replaced by what the volume suggests.

Needs raw stat columns on the history frame (`scored_history(..., keep=RAW_COLUMNS)`).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

OPPORTUNITY_COLUMNS = {
    "QB": ("attempts", "carries"),
    "RB": ("targets", "carries"),
    "WR": ("targets", "carries"),
    "TE": ("targets", "carries"),
}
TD_COLUMNS = ("passing_tds", "rushing_tds", "receiving_tds")
MIN_GAMES_TO_FIT = 200


@dataclass(frozen=True)
class OpportunityFit:
    weights: tuple[float, float]  # fantasy points per unit of each opportunity column
    td_per_opportunity: float  # touchdown points per opportunity


def td_points(df: pd.DataFrame) -> pd.Series:
    """Touchdown points (reference scoring: 4 per pass, 6 per rush or catch)."""
    return 4.0 * df["passing_tds"] + 6.0 * (df["rushing_tds"] + df["receiving_tds"])


def fit_opportunity(history: pd.DataFrame, before_season: int) -> dict[str, OpportunityFit]:
    """Per position, from games in seasons before `before_season` only."""
    prior = history[history["season"] < before_season]
    out: dict[str, OpportunityFit] = {}
    for pos, cols in OPPORTUNITY_COLUMNS.items():
        g = prior[(prior["position"] == pos) & (prior[list(cols)].sum(axis=1) > 0)]
        if len(g) < MIN_GAMES_TO_FIT:
            continue
        x = g[list(cols)].to_numpy(dtype=float)
        weights, *_ = np.linalg.lstsq(x, g["points"].to_numpy(dtype=float), rcond=None)
        opportunities = float(x.sum())
        td_rate = float(td_points(g).sum() / opportunities) if opportunities > 0 else 0.0
        out[pos] = OpportunityFit((float(weights[0]), float(weights[1])), td_rate)
    return out


def expected_points(df: pd.DataFrame, fits: dict[str, OpportunityFit]) -> pd.Series:
    """Expected fantasy points per game from volume; NaN where the position has no fit."""
    out = pd.Series(np.nan, index=df.index)
    for pos, fit in fits.items():
        mask = df["position"] == pos
        a, b = OPPORTUNITY_COLUMNS[pos]
        out[mask] = fit.weights[0] * df.loc[mask, a] + fit.weights[1] * df.loc[mask, b]
    return out


def regress_touchdowns(
    df: pd.DataFrame, fits: dict[str, OpportunityFit], strength: float
) -> pd.Series:
    """Points with `strength` (0..1) of the touchdown points replaced by the expected amount."""
    adjusted = df["points"].copy()
    for pos, fit in fits.items():
        mask = df["position"] == pos
        a, b = OPPORTUNITY_COLUMNS[pos]
        expected = fit.td_per_opportunity * (df.loc[mask, a] + df.loc[mask, b])
        actual = td_points(df.loc[mask])
        adjusted[mask] = df.loc[mask, "points"] - strength * (actual - expected)
    return adjusted


def usage_share(history: pd.DataFrame) -> pd.Series:
    """A player's share of his team's targets and carries in each game."""
    opps = history["targets"] + history["carries"]
    team = opps.groupby([history["team"], history["season"], history["week"]]).transform("sum")
    return (opps / team.where(team > 0)).where(history["position"].isin(["RB", "WR", "TE"]))
