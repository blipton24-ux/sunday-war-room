"""Stats, then score (P4 step 6, ADR-060, ADR-064).

The models predict volume (attempts, carries, targets) and rates per opportunity. Here they
become expected stats (volume x rate), the stats the models do not predict come from
league-average rates per opportunity (`MINOR`), each stat gets a spread learned out of sample
(`fit_spreads`), and the league's own rules score them (`scoring.score` with `variance`, so step
and bonus rules count their expected value). Availability rules then apply: Out, IR, PUP and
Suspended score 0, Doubtful and Questionable keep the 1.0.0 discount for the chance he sits (the
models learned from players who played), and a backup quarterback is discounted.

The example from the P4 Build Plan: 8.1 targets x 66% caught = 5.35 catches x 12.4 yards = 66
yards, 8.1 x 0.055 = 0.45 touchdowns; full PPR 5.35 + 6.6 + 2.7 = 14.6 before minor stats.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from app.model.projection import BACKUP_QB_MULTIPLIER, INJURY_MULTIPLIER
from app.model.scoring import score

if TYPE_CHECKING:
    from app.model.ml.train import ModelSet, TrainingTable

# Stats the models do not predict: (stat, the expected stat it is a rate of). League average
# per position, from the training seasons (too rare or too noisy to model per player).
MINOR: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("sacks_suffered", ("attempts",)),
    ("passing_first_downs", ("completions",)),
    ("rushing_first_downs", ("carries",)),
    ("receiving_first_downs", ("receptions",)),
    ("passing_2pt_conversions", ("attempts",)),
    ("rushing_2pt_conversions", ("carries",)),
    ("receiving_2pt_conversions", ("targets",)),
    ("rushing_fumbles_lost", ("carries",)),
    ("receiving_fumbles_lost", ("receptions",)),
    ("sack_fumbles_lost", ("sacks_suffered",)),
    ("fumbles_total", ("carries", "receptions", "sacks_suffered")),
)
CORE = (
    "attempts", "completions", "passing_yards", "passing_tds", "passing_interceptions",
    "carries", "rushing_yards", "rushing_tds",
    "targets", "receptions", "receiving_yards", "receiving_tds",
)  # fmt: skip
STATS = (*CORE, *(stat for stat, _ in MINOR))
SPREAD_BINS = 8
MIN_SPREAD_ROWS = 50
POISSON = (1.0, 1.0)  # variance = mean, when there is too little to fit a spread

Key = tuple[str, str]  # (position, stat)


def _col(frame: pd.DataFrame, name: str) -> pd.Series:
    if name in frame.columns:
        return frame[name].astype(float).fillna(0.0)
    return pd.Series(0.0, index=frame.index)


def fit_minor_rates(table: TrainingTable) -> dict[Key, float]:
    """League-average rate per opportunity for each MINOR stat, per position."""
    out: dict[Key, float] = {}
    positions = table.features["position"].to_numpy()
    for position in pd.unique(positions):
        rows = table.stats[positions == position]
        for stat, per in MINOR:
            den = sum((_col(rows, p) for p in per), start=pd.Series(0.0, index=rows.index))
            total = float(den.sum())
            out[(str(position), stat)] = float(_col(rows, stat).sum()) / total if total else 0.0
    return out


def expected_stats(
    predictions: pd.DataFrame, positions: pd.Series, minor: Mapping[Key, float]
) -> pd.DataFrame:
    """Expected stats per row from the models' predictions (one column per target name)."""

    def p(name: str, upper: float | None = None) -> pd.Series:
        return _col(predictions, name).clip(lower=0.0, upper=upper)

    out = pd.DataFrame(index=predictions.index)
    out["attempts"] = p("attempts")
    out["completions"] = out["attempts"] * p("completion_rate", 1.0)
    out["passing_yards"] = out["attempts"] * _col(predictions, "yards_per_attempt")
    out["passing_tds"] = out["attempts"] * p("pass_td_rate")
    out["passing_interceptions"] = out["attempts"] * p("int_rate")
    out["carries"] = p("carries")
    out["rushing_yards"] = out["carries"] * _col(predictions, "yards_per_carry")
    out["rushing_tds"] = out["carries"] * p("rush_td_rate")
    out["targets"] = p("targets")
    out["receptions"] = out["targets"] * p("catch_rate", 1.0)
    out["receiving_yards"] = out["receptions"] * _col(predictions, "yards_per_catch")
    out["receiving_tds"] = out["targets"] * p("rec_td_rate")
    pos = positions.to_numpy()
    for stat, per in MINOR:  # in order: sack fumbles read the sacks set just before
        base = sum((out[x] for x in per), start=pd.Series(0.0, index=out.index))
        rate = np.array([minor.get((str(x), stat), 0.0) for x in pos], dtype=float)
        out[stat] = base * rate
    return out


def fit_spreads(
    expected: pd.DataFrame, actual: pd.DataFrame, positions: pd.Series
) -> dict[Key, tuple[float, float]]:
    """How far real stats land from the expected ones, per position and stat, as
    variance = a x expected ** b (fit on out-of-sample predictions by binning the expected
    value). Too few rows, or no clear pattern: variance = expected (Poisson)."""
    out: dict[Key, tuple[float, float]] = {}
    pos = positions.to_numpy()
    for position in pd.unique(pos):
        at = pos == position
        for stat in STATS:
            mu = expected.loc[at, stat].to_numpy(dtype=float)
            y = _col(actual.loc[at], stat).to_numpy(dtype=float)
            ok = mu > 0
            if ok.sum() < MIN_SPREAD_ROWS:
                out[(str(position), stat)] = POISSON
                continue
            frame = pd.DataFrame({"mu": mu[ok], "sq": (y[ok] - mu[ok]) ** 2})
            frame["bin"] = pd.qcut(frame["mu"], SPREAD_BINS, labels=False, duplicates="drop")
            bins = frame.groupby("bin").agg(mu=("mu", "mean"), var=("sq", "mean"), n=("mu", "size"))
            bins = bins[(bins["var"] > 0) & (bins["mu"] > 0)]
            if len(bins) < 3:
                out[(str(position), stat)] = POISSON
                continue
            b, log_a = np.polyfit(np.log(bins["mu"]), np.log(bins["var"]), 1, w=np.sqrt(bins["n"]))
            out[(str(position), stat)] = (float(np.exp(log_a)), float(np.clip(b, 0.0, 3.0)))
    return out


def stat_variance(
    expected: pd.DataFrame, positions: pd.Series, spreads: Mapping[Key, tuple[float, float]]
) -> pd.DataFrame:
    """Each expected stat's variance from the fitted spreads (0 where the stat is 0)."""
    out = pd.DataFrame(index=expected.index)
    pos = positions.to_numpy()
    for stat in STATS:
        mu = expected[stat].to_numpy(dtype=float)
        a = np.array([spreads.get((str(x), stat), POISSON)[0] for x in pos], dtype=float)
        b = np.array([spreads.get((str(x), stat), POISSON)[1] for x in pos], dtype=float)
        out[stat] = np.where(mu > 0, a * np.power(np.maximum(mu, 1e-12), b), 0.0)
    return out


def availability(targets: pd.DataFrame) -> pd.Series:
    """The 1.0.0 availability multiplier from live status (backtests carry no such columns):
    Out, IR, PUP, Suspended 0; Doubtful 0.25; Questionable 0.92; a backup QB 0.25."""
    mult = pd.Series(1.0, index=targets.index)
    if "injury_status" in targets.columns:
        status = targets["injury_status"].fillna("").astype(str).str.strip().str.lower()
        mult *= status.map(INJURY_MULTIPLIER).fillna(1.0).astype(float)
    if "depth_chart_order" in targets.columns:
        depth = pd.to_numeric(targets["depth_chart_order"], errors="coerce")
        backup = (targets["position"] == "QB") & (depth >= 2)
        mult = mult.where(~backup, mult * BACKUP_QB_MULTIPLIER)
    return mult


def project(models: ModelSet, features: pd.DataFrame, rules: Mapping[str, float]) -> pd.DataFrame:
    """Points for every row of `features` (build_features output, plus `injury_status` and
    `depth_chart_order` when live) under one league's rules. Returns `points`, the multiplier
    applied, and every expected stat (`exp_<stat>`)."""
    positions = features["position"]
    expected = expected_stats(models.predict(features), positions, models.minor)
    variance = stat_variance(expected, positions, models.spreads)
    raw = score(expected.assign(position=positions), rules, variance.assign(position=positions))
    mult = availability(features)
    out = pd.DataFrame(index=features.index)
    out["points"] = (raw.clip(lower=0.0) * mult).round(2)
    out["availability"] = mult
    for stat in STATS:
        out[f"exp_{stat}"] = expected[stat]
    return out
