"""Grading definitions (ADR-031 #3), shared by the backtest and the live Accuracy page so both
measure the same way.

Input frame columns: position, season, week, proj, actual, and optionally p10, p90.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

BUCKETS = (0, 5, 10, 15, 20, np.inf)
BUCKET_LABELS = ("0-5", "5-10", "10-15", "15-20", "20+")


def _rank_corr(df: pd.DataFrame) -> float:
    """Spearman correlation within each position-week, averaged: does the order hold up?

    This is what start/sit depends on, and a low MAE can hide a poor ordering.
    """
    corrs = []
    for _, g in df.groupby(["position", "season", "week"]):
        if len(g) >= 5 and g["proj"].nunique() > 1 and g["actual"].nunique() > 1:
            corrs.append(g["proj"].rank().corr(g["actual"].rank()))
    return float(np.mean(corrs)) if corrs else float("nan")


def grade(df: pd.DataFrame) -> dict[str, Any]:
    err = df["proj"] - df["actual"]
    out: dict[str, Any] = {
        "n": len(df),
        "mae": float(err.abs().mean()),
        "rmse": float(np.sqrt((err**2).mean())),
        "bias": float(err.mean()),  # + means projections run high
        "rank_corr": _rank_corr(df),
    }
    if {"p10", "p90"} <= set(df.columns):
        inside = (df["actual"] >= df["p10"]) & (df["actual"] <= df["p90"])
        out["coverage_80"] = float(inside.mean())
    buckets = pd.cut(df["proj"], BUCKETS, labels=BUCKET_LABELS, right=False)
    out["mae_by_bucket"] = {
        str(k): round(float(v), 2)
        for k, v in err.abs().groupby(buckets, observed=True).mean().items()
    }
    return out


def grade_by_position(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {str(pos): grade(g) for pos, g in df.groupby("position")}


# --------------------------------------------------------------------------- startable players
# Who a manager would plausibly start: each week's top QBs and TEs, and top RBs and WRs
# (about a 12-team league's starters plus flex). K and DEF are not part of the slice.
STARTABLE_TOP = {"QB": 15, "TE": 15, "RB": 36, "WR": 36}


def startable_mask(df: pd.DataFrame, by: str = "naive") -> pd.Series:
    """True for the startable rows of each position-week, ranked by column `by`.

    Rank by a column that does not depend on the model being judged (the default, the plain
    season average), so two models are graded on the same players. Ranking by `proj` shows the
    players a given model would actually start; ADR-034's 6.35 / 6.45 came from that.
    """
    limit = df["position"].map(STARTABLE_TOP)
    rank = df.groupby(["position", "season", "week"])[by].rank(method="first", ascending=False)
    return (rank <= limit).fillna(False)


def week_group(df: pd.DataFrame) -> pd.Series:
    """'1-4' (the opener, a harder problem with little history) or '5+'."""
    return pd.Series(np.where(df["week"] <= 4, "1-4", "5+"), index=df.index)
