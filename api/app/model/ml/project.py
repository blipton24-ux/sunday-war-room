"""Stats, then score (P4 step 6, ADR-060, ADR-064).

The models predict volume (attempts, carries, targets) and rates per opportunity. Here they
become expected stats (volume x rate), the stats the models do not predict come from
league-average rates per opportunity (`MINOR`), each stat gets a spread learned out of sample
(`fit_spreads`), and the league's own rules score them (`scoring.score` with `variance`, so step
and bonus rules count their expected value). Availability (ADR-068): Out, IR, PUP and Suspended
score 0; a Questionable or Doubtful player is projected as if he plays, less the fitted trim for
playing hurt, and carries the fitted chance he plays (`p_play`) and the chance-weighted value
(`expected`) beside it; a backup quarterback is discounted.

The example from the P4 Build Plan: 8.1 targets x 66% caught = 5.35 catches x 12.4 yards = 66
yards, 8.1 x 0.055 = 0.45 touchdowns; full PPR 5.35 + 6.6 + 2.7 = 14.6 before minor stats.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from app.model.projection import BACKUP_QB_MULTIPLIER, INJURY_MULTIPLIER
from app.model.scoring import REFERENCE_RULES, score

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

# Availability (ADR-068). The statuses that get a chance to play and a trim; the feature table
# codes the final report as 1 Questionable, 2 Doubtful.
PLAY_STATUSES = ("questionable", "doubtful")
REPORT_CODE_STATUS = {1.0: "questionable", 2.0: "doubtful"}
# The last practice that week (ADR-069), from the feature table's code or nflverse's wording;
# "" when there is no practice report (a status from Sleeper with no report behind it).
PRACTICE_CODE_NAME = {1.0: "full", 2.0: "limited", 3.0: "none"}
PRACTICE_NAME = {
    "Full Participation in Practice": "full",
    "Limited Participation in Practice": "limited",
    "Did Not Participate In Practice": "none",
}
# Before a fit (or for a group never seen): 2016-2025 rates, skill positions (ADR-068).
DEFAULT_PLAY = {"questionable": 0.65, "doubtful": 0.01}
PLAY_PRIOR = 20  # games: a thin group leans on the rate one level up (ADR-068, ADR-069)
TRIM_PRIOR = 50  # games: with few Questionable games the trim stays near 1
TRIM_LIMITS = (0.7, 1.05)

Key = tuple[str, str]  # (position, stat)
PlayKey = tuple[str, str, bool, str]  # (position, status, starter, practice)
ANY_POSITION = "*"  # the status-and-practice rate, for a group never seen


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


def shrink(hits: float, games: int, toward: float) -> float:
    """`hits` out of `games`, pulled toward `toward` by PLAY_PRIOR pretend games."""
    return (hits + PLAY_PRIOR * toward) / (games + PLAY_PRIOR)


def fit_play_rates(reports: pd.DataFrame) -> dict[PlayKey, float]:
    """Chance he plays, per (position, status, starter, practice), from `reports`: one row per
    skill player listed Questionable or Doubtful, with `position`, `report_status`, `starter`
    (depth tier 1 that week), `practice` (last practice: full, limited, none or "") and `played`
    (an offensive snap). Shrunk in two levels: a group leans on its status-and-practice rate,
    which leans on its status's overall rate. The status-and-practice rates are kept too, under
    position ANY_POSITION, for a group never seen."""
    out: dict[PlayKey, float] = {}
    if reports.empty:
        return out
    status = reports["report_status"].astype(str).str.lower()
    practice = reports["practice"].fillna("").astype(str)
    for name in PLAY_STATUSES:
        rows = reports[status == name]
        if rows.empty:
            continue
        overall = float(rows["played"].astype(float).mean())
        for level, same in rows.groupby(practice[status == name]):
            level_played = float(same["played"].astype(float).sum())
            target = shrink(level_played, len(same), overall)
            out[(ANY_POSITION, name, False, str(level))] = target
            for (position, starter), g in same.groupby(["position", "starter"]):
                played = float(g["played"].astype(float).sum())
                out[(str(position), name, bool(starter), str(level))] = shrink(
                    played, len(g), target
                )
    return out


def shrink_trim(ratio: float, games: int) -> float:
    """The trim for one position: `ratio` is how Questionable/Doubtful players who played scored
    against their projection, relative to everyone else (0.9 = 10% under), from `games` games
    in the held-back season. Returns the multiplier to apply to their projection."""
    blended = (ratio * games + 1.0 * TRIM_PRIOR) / (games + TRIM_PRIOR)
    low, high = TRIM_LIMITS
    return max(low, min(blended, high))


def fit_trim(
    expected: pd.DataFrame, actual: pd.DataFrame, positions: pd.Series, status: pd.Series
) -> dict[str, float]:
    """Per position: actual over projected points for players listed Questionable or Doubtful
    who played, relative to the same ratio for everyone else, out of sample. Points use
    Sleeper's half PPR only to weight the stats; each league's own rules score projections."""
    exp = score(expected.assign(position=positions), REFERENCE_RULES)
    real = actual.reindex(columns=list(STATS)).fillna(0.0)
    act = score(real.assign(position=positions), REFERENCE_RULES)
    listed = status.isin(PLAY_STATUSES).to_numpy()
    out: dict[str, float] = {}
    for position in pd.unique(positions):
        at = (positions == position).to_numpy()
        hurt, rest = at & listed, at & ~listed
        if not hurt.any() or exp[rest].sum() <= 0 or exp[hurt].sum() <= 0:
            continue
        ratio = (act[hurt].sum() / exp[hurt].sum()) / (act[rest].sum() / exp[rest].sum())
        out[str(position)] = shrink_trim(float(ratio), int(hurt.sum()))
    return out


def report_status(features: pd.DataFrame) -> pd.Series:
    """Lower-case status per row: the live `injury_status` where given, else the final report
    from the feature table (backtests), else ""."""
    out = pd.Series("", index=features.index)
    if "report_status" in features.columns:
        out = features["report_status"].map(REPORT_CODE_STATUS).fillna("").astype(str)
    if "injury_status" in features.columns:
        live = features["injury_status"].fillna("").astype(str).str.strip().str.lower()
        out = live.where(live != "", out)
    return out


def practice_status(features: pd.DataFrame) -> pd.Series:
    """Last practice per row (full, limited, none) from the feature table's code, else ""."""
    if "practice_status" not in features.columns:
        return pd.Series("", index=features.index)
    return features["practice_status"].map(PRACTICE_CODE_NAME).fillna("").astype(str)


def play_rate(
    rates: Mapping[PlayKey, float], position: str, status: str, starter: bool, practice: str
) -> float:
    """The fitted chance he plays; a group never seen falls back to its status-and-practice
    rate, then to DEFAULT_PLAY."""
    exact = rates.get((position, status, starter, practice))
    if exact is not None:
        return exact
    return rates.get((ANY_POSITION, status, False, practice), DEFAULT_PLAY[status])


def availability(
    features: pd.DataFrame,
    trim: Mapping[str, float] | None = None,
    play_rates: Mapping[PlayKey, float] | None = None,
) -> pd.DataFrame:
    """Per row: `mult`, applied to the projection (0 for Out, IR, PUP, Suspended; the trim for
    Questionable and Doubtful; the backup QB discount), and `p_play`, the chance he plays."""
    status = report_status(features)
    positions = features["position"].astype(str)
    starter = (
        pd.to_numeric(features["depth_tier"], errors="coerce").eq(1)
        if "depth_tier" in features.columns
        else pd.Series(True, index=features.index)
    )
    zero = status.map(INJURY_MULTIPLIER).eq(0.0) & ~status.isin(PLAY_STATUSES)
    listed = status.isin(PLAY_STATUSES)
    trims = positions.map(lambda p: (trim or {}).get(p, 1.0)).astype(float)
    mult = pd.Series(1.0, index=features.index).where(~listed, trims).where(~zero, 0.0)
    practice = practice_status(features)
    rates = [
        play_rate(play_rates or {}, p, s, bool(t), pr) if s in PLAY_STATUSES else 1.0
        for p, s, t, pr in zip(positions, status, starter, practice, strict=True)
    ]
    p_play = pd.Series(rates, index=features.index, dtype=float).where(~zero, 0.0)
    if "depth_chart_order" in features.columns:
        depth = pd.to_numeric(features["depth_chart_order"], errors="coerce")
        backup = (positions == "QB") & (depth >= 2)
        mult = mult.where(~backup, mult * BACKUP_QB_MULTIPLIER)
    return pd.DataFrame({"mult": mult, "p_play": p_play})


def project(models: ModelSet, features: pd.DataFrame, rules: Mapping[str, float]) -> pd.DataFrame:
    """Points for every row of `features` (build_features output, plus `injury_status` and
    `depth_chart_order` when live) under one league's rules. Returns `points` (as if he plays,
    ADR-068), `p_play`, `expected` (points x p_play, for win probability and team totals), the
    multiplier applied, and every expected stat (`exp_<stat>`)."""
    positions = features["position"]
    expected = expected_stats(models.predict(features), positions, models.minor)
    variance = stat_variance(expected, positions, models.spreads)
    raw = score(expected.assign(position=positions), rules, variance.assign(position=positions))
    avail = availability(features, models.trim, models.play_rates)
    out = pd.DataFrame(index=features.index)
    out["points"] = (raw.clip(lower=0.0) * avail["mult"]).round(2)
    out["p_play"] = avail["p_play"].round(3)
    out["expected"] = (out["points"] * out["p_play"]).round(2)
    out["availability"] = avail["mult"]
    for stat in STATS:
        out[f"exp_{stat}"] = expected[stat]
    return out
