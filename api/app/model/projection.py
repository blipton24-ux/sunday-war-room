"""Projection model v1 (docs/Specs/Projection-Model.md). Pure: DataFrames in, DataFrame out.

For one target week (season S, week W) and a set of players:

1. score history with the league's rules            (done by the caller via scoring.score)
2. baseline   recency-weighted mean of season-S games before W, blended with season S-1
3. opponent   how much this week's opponent allows to the position, clamped and faded early
4. role       recent snap share vs the player's season share (RB/WR/TE), clamped
5. injury     Out/IR -> 0, Doubtful/Questionable discounted; backup QBs heavily discounted
6. range      p10/p50/p90 from backtested residual quantiles (app/model/distribution.py)

Every step appends a factor {name, value, effect, note} so the UI can show "why this number".
**Only data from before week W is used** (walk-forward safe), which is what makes the
backtest honest and lets projections be frozen at kickoff.

Bump MODEL_VERSION in the same commit as any change to the math (Integrity rules).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.model.config import SHIPPED, ModelConfig
from app.model.distribution import Calibration, apply_range
from app.model.features.injury_games import excluded

MODEL_VERSION = "1.0.0"

HALF_LIFE_GAMES = 4.0  # a game 4 games ago counts half as much as the latest one
PRIOR_GAMES = 3.0  # last season's average counts like this many games of this season
PRIOR_QUANTILE = 0.30  # no-history players start at the 30th percentile of their position
OPP_CLAMP = 0.25  # opponent effect limited to +-25%
OPP_FADE_GAMES = 4.0  # ...and weighted n/(n+4): week 2 barely moves, week 10 mostly trusted
ROLE_CLAMP = 0.15
ROLE_POSITIONS = frozenset({"RB", "WR", "TE"})
INJURY_MULTIPLIER = {
    "out": 0.0, "ir": 0.0, "pup": 0.0, "sus": 0.0, "na": 0.0, "cov": 0.0,
    "doubtful": 0.25, "questionable": 0.92,
}  # fmt: skip
BACKUP_QB_MULTIPLIER = 0.25

HISTORY_COLUMNS = ("gsis_id", "season", "week", "position", "team", "opponent", "points", "snap")
TARGET_COLUMNS = ("gsis_id", "position", "team", "opponent")  # + optional injury/depth columns


@dataclass(frozen=True)
class Context:
    season: int
    week: int


def _factor(name: str, value: float, effect: float, note: str) -> dict[str, Any]:
    return {"name": name, "value": round(value, 3), "effect": round(effect, 2), "note": note}


def _ewm(points: np.ndarray) -> float:
    n = len(points)
    weights = 0.5 ** ((n - 1 - np.arange(n)) / HALF_LIFE_GAMES)
    return float(np.dot(points, weights) / weights.sum())


def _opponent_table(
    cur: pd.DataFrame,
) -> tuple[dict[tuple[str, str], tuple[float, int]], dict[str, float]]:
    """(opponent, position) -> (avg points the position scored vs them per game, games)."""
    if cur.empty:
        return {}, {}
    per_game = cur.groupby(["opponent", "position", "season", "week"], as_index=False)[
        "points"
    ].sum()
    by_opp = per_game.groupby(["opponent", "position"])["points"].agg(["mean", "count"])
    league = by_opp.groupby(level="position")["mean"].mean().to_dict()
    table = {k: (float(r["mean"]), int(r["count"])) for k, r in by_opp.iterrows()}
    return table, {str(k): float(v) for k, v in league.items()}


def position_priors(last: pd.DataFrame, cur: pd.DataFrame) -> dict[str, float]:
    """Starting point for players with no history: a low-but-rosterable per-game value."""
    source = last if not last.empty else cur
    if source.empty:
        return {}
    per_player = source.groupby(["position", "gsis_id"])["points"].mean().reset_index()
    q = per_player.groupby("position")["points"].quantile(PRIOR_QUANTILE)
    return {str(k): float(v) for k, v in q.items()}


def project_week(
    history: pd.DataFrame,
    targets: pd.DataFrame,
    ctx: Context,
    calibration: Calibration | None,
    config: ModelConfig = SHIPPED,
) -> pd.DataFrame:
    """Project every row of `targets` for ctx.season / ctx.week.

    history: one row per player-game with HISTORY_COLUMNS, points already scored with the
             league's rules. Rows at or after the target week are ignored (no leakage).
    targets: TARGET_COLUMNS; `opponent` None means no game (bye). Optional columns:
             `injury_status`, `depth_chart_order`.
    config:  switches for ideas under test (app/model/config.py); live code uses SHIPPED.
    Returns targets + points, p10, p50, p90, factors.
    """
    hist = history[
        (history["season"] < ctx.season)
        | ((history["season"] == ctx.season) & (history["week"] < ctx.week))
    ]
    if config.skip_injury_games_in_history and "injury_game" in hist.columns:
        hist = hist[~excluded(hist["injury_game"])]
    cur = hist[hist["season"] == ctx.season]
    last = hist[hist["season"] == ctx.season - 1]
    opp_table, opp_league = _opponent_table(cur)
    priors = position_priors(last, cur)

    cur_by = {k: g.sort_values("week") for k, g in cur.groupby("gsis_id")}
    last_mean = last.groupby("gsis_id")["points"].agg(["mean", "count"])
    last_by = {k: (float(r["mean"]), int(r["count"])) for k, r in last_mean.iterrows()}

    out_rows = []
    for t in targets.to_dict("records"):
        gid, pos, opp = t["gsis_id"], t["position"], t.get("opponent")
        factors: list[dict[str, Any]] = []

        # -- 2. baseline ----------------------------------------------------------
        games = cur_by.get(gid)
        n = 0 if games is None else len(games)
        prev = last_by.get(gid)
        if n == 0 and prev is None:
            base = float(priors.get(pos, 0.0))
            note = f"No NFL history yet: starts at a typical low-end {pos} value"
        else:
            recent = _ewm(games["points"].to_numpy()) if games is not None else 0.0
            prior = prev[0] if prev else float(priors.get(pos, recent))
            base = (n * recent + PRIOR_GAMES * prior) / (n + PRIOR_GAMES)
            parts = []
            if n:
                parts.append(f"{n} game{'s' * (n != 1)} this season (recent-weighted {recent:.1f})")
            parts.append(
                f"{ctx.season - 1} average {prev[0]:.1f} over {prev[1]} games"
                if prev
                else f"typical {pos} value {prior:.1f} (no {ctx.season - 1} games)"
            )
            note = "Blend of " + " and ".join(parts)
        pts = base
        factors.append(_factor("baseline", base, base, note))

        # -- bye ------------------------------------------------------------------
        if opp is None or (isinstance(opp, float) and np.isnan(opp)):
            factors.append(_factor("bye", 0.0, -pts, "No game this week"))
            out_rows.append({**t, "raw_points": 0.0, "factors": factors})
            continue

        # -- 3. opponent ----------------------------------------------------------
        allowed = opp_table.get((opp, pos))
        avg = opp_league.get(pos)
        if allowed and avg and avg > 0:
            ratio = allowed[0] / avg
            weight = allowed[1] / (allowed[1] + OPP_FADE_GAMES)
            mult = 1.0 + float(np.clip(ratio - 1.0, -OPP_CLAMP, OPP_CLAMP)) * weight
            direction = "more" if ratio >= 1 else "less"
            note = (
                f"{opp} has allowed {abs(ratio - 1):.0%} {direction} than average to {pos}s "
                f"({allowed[1]} games; trusted {weight:.0%} this early)"
            )
        else:
            mult, note = 1.0, f"Not enough {ctx.season} games to rate {opp} yet"
        factors.append(_factor("opponent", mult, pts * (mult - 1), note))
        pts *= mult

        # -- 4. role --------------------------------------------------------------
        if pos in ROLE_POSITIONS and games is not None and n >= 3:
            snaps = games["snap"].dropna().to_numpy()
            if len(snaps) >= 3 and snaps.mean() > 0:
                ratio = snaps[-2:].mean() / snaps.mean()
                mult = 1.0 + float(np.clip(ratio - 1.0, -ROLE_CLAMP, ROLE_CLAMP))
                note = (
                    f"Snap share last 2 games {snaps[-2:].mean():.0%} vs season {snaps.mean():.0%}"
                )
                factors.append(_factor("role", mult, pts * (mult - 1), note))
                pts *= mult

        # -- 5. depth + injury (live data only; not in the backtest) ---------------
        depth = t.get("depth_chart_order")
        if pos == "QB" and depth is not None and not pd.isna(depth) and int(depth) >= 2:
            mult = BACKUP_QB_MULTIPLIER
            factors.append(
                _factor("depth", mult, pts * (mult - 1), f"QB{int(depth)} on depth chart")
            )
            pts *= mult
        status = str(t.get("injury_status") or "").strip()
        if status:
            mult = INJURY_MULTIPLIER.get(status.lower(), 1.0)
            if mult != 1.0:
                factors.append(_factor("injury", mult, pts * (mult - 1), f"Listed {status}"))
                pts *= mult

        out_rows.append(
            {**t, "raw_points": max(pts, 0.0) if pos != "DEF" else pts, "factors": factors}
        )

    out = pd.DataFrame(out_rows)
    if out.empty:
        return out.assign(points=[], p10=[], p50=[], p90=[])
    out["points"] = out["raw_points"].round(2)
    if calibration is not None:
        ranges = [
            apply_range(p, pos, calibration)
            for p, pos in zip(out["raw_points"], out["position"], strict=True)
        ]
        out["p10"], out["p50"], out["p90"] = zip(*ranges, strict=True)
    return out.drop(columns=["raw_points"])
