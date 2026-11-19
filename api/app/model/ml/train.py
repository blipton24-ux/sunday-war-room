"""Training the P4 models (step 5, ADR-061): one XGBoost model per position and target.

Settings are chosen inside the training seasons only: the last training season is held back,
each candidate in `GRID` is trained on the seasons before it with early stopping on it, and the
best is then retrained on every training season. A test season is never seen. Training is
repeatable: the same seasons and settings give the same model (fixed seed).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb

from app.model.ml.data import ModelData
from app.model.ml.features import SKILL, TARGET_COLUMNS, build_features, feature_columns
from app.model.ml.project import (
    Key,
    expected_stats,
    fit_minor_rates,
    fit_play_rates,
    fit_spreads,
    fit_trim,
    report_status,
)
from app.model.ml.targets import BY_POSITION, Target, label

SEED = 2026
LEARNING_RATE = 0.05
MAX_TREES = 2000
EARLY_STOPPING = 50
BASE_PARAMS: dict[str, Any] = {
    "eta": LEARNING_RATE,
    "subsample": 0.8,
    "tree_method": "hist",
    "seed": SEED,
    "verbosity": 0,
}
# Candidate settings tried for every model; the held-back season picks one.
GRID: tuple[dict[str, Any], ...] = tuple(
    {"max_depth": depth, "min_child_weight": leaf, "colsample_bytree": columns}
    for depth in (3, 5)
    for leaf in (10, 50, 200)
    for columns in (0.5, 0.8)
)
OBJECTIVE = {"count": ("count:poisson", "poisson-nloglik"), "rate": ("reg:squarederror", "rmse")}


REPORT_COLUMNS = ["gsis_id", "season", "week", "position", "report_status", "starter", "played"]


@dataclass(frozen=True)
class TrainingTable:
    """`features`: build_features output, one row per player-game. `stats`: the same rows' raw
    stat columns, which the labels come from. Kept apart so a label can never become an input.
    `reports`: skill players listed Questionable or Doubtful, whether or not they then played
    (`injury_reports`), for the chance he plays (ADR-068)."""

    features: pd.DataFrame
    stats: pd.DataFrame
    reports: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=REPORT_COLUMNS))

    def _keep(self, keep: np.ndarray, reports: np.ndarray) -> TrainingTable:
        return TrainingTable(
            self.features[keep].reset_index(drop=True),
            self.stats[keep].reset_index(drop=True),
            self.reports[reports].reset_index(drop=True),
        )

    def seasons(self, seasons: Sequence[int]) -> TrainingTable:
        keep = self.features["season"].isin(list(seasons)).to_numpy()
        return self._keep(keep, self.reports["season"].isin(list(seasons)).to_numpy())

    def before(self, season: int, week: int) -> TrainingTable:
        """Every row played before `week` of `season`: what a model trained that Tuesday sees."""

        def keep(f: pd.DataFrame) -> np.ndarray:
            return (
                (f["season"] < season) | ((f["season"] == season) & (f["week"] < week))
            ).to_numpy()

        return self._keep(keep(self.features), keep(self.reports))


def report_rows(data: ModelData, seasons: Sequence[int]) -> pd.DataFrame:
    """Skill players listed Questionable or Doubtful whose week's snap counts are known: his
    position (from his games), whether he was a starter (depth tier 1) and whether he played."""
    inj = data.injuries
    if inj.empty or "played" not in inj.columns:
        return pd.DataFrame(columns=REPORT_COLUMNS)
    status = inj["report_status"].fillna("").astype(str).str.lower()
    rows = inj[status.isin(["questionable", "doubtful"]) & inj["played"].notna()]
    rows = rows[rows["season"].isin(list(seasons))]
    position = data.stats.drop_duplicates("gsis_id", keep="last").set_index("gsis_id")["position"]
    rows = rows.assign(position=rows["gsis_id"].map(position))
    rows = rows[rows["position"].isin(SKILL)]
    tier = data.depth.drop_duplicates(["gsis_id", "season", "week"])
    rows = rows.merge(tier, on=["gsis_id", "season", "week"], how="left")
    rows = rows.assign(starter=rows["depth_tier"].eq(1), played=rows["played"].astype(bool))
    return rows[REPORT_COLUMNS].reset_index(drop=True)


def training_table(data: ModelData, seasons: Sequence[int]) -> TrainingTable:
    """Every skill-position player-game in `seasons`, with its features and raw stats."""
    s = data.stats
    games = s[s["position"].isin(SKILL) & s["season"].isin(list(seasons))].reset_index(drop=True)
    features = build_features(data, games[list(TARGET_COLUMNS)])
    return TrainingTable(features, games, report_rows(data, seasons))


@dataclass
class FittedModel:
    position: str
    target: Target
    booster: xgb.Booster
    params: dict[str, Any]
    trees: int
    features: list[str]
    train_seasons: list[int]
    holdout_score: float
    # The chosen settings trained without the held-back season: used once, to learn how far
    # real stats land from predictions (spreads). Not saved.
    inner: xgb.Booster | None = None
    inner_trees: int = 0

    def predict(self, features: pd.DataFrame, inner: bool = False) -> np.ndarray:
        matrix = xgb.DMatrix(features[self.features].astype(float), missing=np.nan)
        if inner:
            if self.inner is None:
                raise ValueError("this model has no held-back version (loaded from files)")
            return np.asarray(
                self.inner.predict(matrix, iteration_range=(0, self.inner_trees)), dtype=float
            )
        return np.asarray(self.booster.predict(matrix), dtype=float)


def _rows(
    table: TrainingTable, position: str, target: Target
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    at = (table.features["position"] == position).to_numpy()
    value, weight = label(table.stats[at], target)
    usable = (weight > 0).to_numpy() & np.isfinite(value.to_numpy())
    feats = table.features[at][usable]
    return feats, value.to_numpy()[usable], weight.to_numpy()[usable]


def _matrix(feats: pd.DataFrame, columns: list[str], y: np.ndarray, w: np.ndarray) -> xgb.DMatrix:
    return xgb.DMatrix(feats[columns].astype(float), label=y, weight=w, missing=np.nan)


def fit(
    table: TrainingTable,
    position: str,
    target: Target,
    train_seasons: Sequence[int],
    grid: Sequence[dict[str, Any]] = GRID,
    upto: tuple[int, int] | None = None,
) -> FittedModel:
    """Choose settings on the last training season, then retrain on all of them.

    `upto=(season, week)`: the final retrain also learns from that season's games before
    `week` (ADR-065); settings are still chosen on the last full training season."""
    seasons = sorted(set(train_seasons))
    if len(seasons) < 2:
        raise ValueError("training needs at least two seasons: one is held back to pick settings")
    columns = feature_columns(table.features)
    held = seasons[-1]
    feats, y, w = _rows(table.seasons(seasons), position, target)
    inner = (feats["season"] < held).to_numpy()
    objective, metric = OBJECTIVE[target.kind]
    d_inner = _matrix(feats[inner], columns, y[inner], w[inner])
    d_held = _matrix(feats[~inner], columns, y[~inner], w[~inner])

    best: tuple[float, dict[str, Any], int, xgb.Booster] | None = None
    for settings in grid:
        params = {**BASE_PARAMS, **settings, "objective": objective, "eval_metric": metric}
        booster = xgb.train(
            params, d_inner, num_boost_round=MAX_TREES, evals=[(d_held, "held")],
            early_stopping_rounds=EARLY_STOPPING, verbose_eval=False,
        )  # fmt: skip
        score = float(booster.best_score)
        if best is None or score < best[0]:
            best = (score, params, booster.best_iteration + 1, booster)
    assert best is not None
    score, params, trees, inner_booster = best
    if upto is not None:
        feats, y, w = _rows(table.seasons([*seasons, upto[0]]).before(*upto), position, target)
    # retrain on every training row; more rows support proportionally more trees
    trees_all = min(MAX_TREES, round(trees * len(y) / max(1, int(inner.sum()))))
    booster = xgb.train(params, _matrix(feats, columns, y, w), num_boost_round=trees_all)
    return FittedModel(
        position, target, booster, params, trees_all, columns, seasons, score, inner_booster, trees
    )


@dataclass
class ModelSet:
    """Every fitted model for one training run, keyed by (position, target name)."""

    models: dict[tuple[str, str], FittedModel] = field(default_factory=dict)
    minor: dict[Key, float] = field(default_factory=dict)  # league-average minor-stat rates
    spreads: dict[Key, tuple[float, float]] = field(default_factory=dict)  # variance = a*mean^b
    trim: dict[str, float] = field(default_factory=dict)  # Questionable/Doubtful who play
    play_rates: dict[tuple[str, str, bool], float] = field(default_factory=dict)  # ADR-068

    def predict(self, features: pd.DataFrame, inner: bool = False) -> pd.DataFrame:
        """One column per target name; a row gets values only from its own position's models.
        `inner`: use the versions trained without the held-back season."""
        out = pd.DataFrame(index=features.index)
        for (position, name), model in self.models.items():
            at = (features["position"] == position).to_numpy()
            if name not in out.columns:
                out[name] = np.nan
            if at.any():
                out.loc[at, name] = model.predict(features[at], inner)
        return out


def train_all(
    table: TrainingTable,
    train_seasons: Sequence[int],
    positions: Sequence[str] = SKILL,
    grid: Sequence[dict[str, Any]] = GRID,
    upto: tuple[int, int] | None = None,
) -> ModelSet:
    out = ModelSet()
    for position in positions:
        for target in BY_POSITION[position]:
            out.models[(position, target.name)] = fit(
                table, position, target, train_seasons, grid, upto
            )
    seasons = sorted(set(train_seasons))
    held, before = table.seasons(seasons[-1:]), table.seasons(seasons[:-1])
    keep = held.features["position"].isin(list(positions)).to_numpy()
    held = TrainingTable(held.features[keep], held.stats[keep])
    # spreads: out-of-sample, from the held-back versions predicting the held-back season
    expected = expected_stats(
        out.predict(held.features, inner=True), held.features["position"], fit_minor_rates(before)
    )
    out.spreads = fit_spreads(expected, held.stats, held.features["position"])
    # the trim for playing hurt: out of sample too, on the same held-back predictions
    out.trim = fit_trim(
        expected, held.stats, held.features["position"], report_status(held.features)
    )
    everything = table.seasons(seasons)
    if upto is not None:
        everything = table.seasons([*seasons, upto[0]]).before(*upto)
    out.minor = fit_minor_rates(everything)
    reports = everything.reports
    out.play_rates = fit_play_rates(reports[reports["position"].isin(list(positions))])
    return out


# --------------------------------------------------------------------------- files
META = "models.json"


def save(models: ModelSet, directory: Path) -> None:
    """Each model as XGBoost JSON, plus models.json with its seasons, settings and columns."""
    directory.mkdir(parents=True, exist_ok=True)
    meta: dict[str, Any] = {
        "xgboost": xgb.__version__,
        "models": [],
        "minor": [[p, s, r] for (p, s), r in models.minor.items()],
        "spreads": [[p, s, a, b] for (p, s), (a, b) in models.spreads.items()],
        "trim": models.trim,
        "play_rates": [[p, s, t, r] for (p, s, t), r in models.play_rates.items()],
    }
    for (position, name), m in models.models.items():  # order kept for load()
        file = f"{position}_{name}.json"
        m.booster.save_model(str(directory / file))
        meta["models"].append(
            {"position": position, "target": name, "file": file, "params": m.params,
             "trees": m.trees, "features": m.features, "train_seasons": m.train_seasons,
             "holdout_score": m.holdout_score}
        )  # fmt: skip
    (directory / META).write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")


def load(directory: Path) -> ModelSet:
    meta = json.loads((directory / META).read_text(encoding="utf-8"))
    targets = {t.name: t for ts in BY_POSITION.values() for t in ts}
    out = ModelSet(
        minor={(p, s): float(r) for p, s, r in meta["minor"]},
        spreads={(p, s): (float(a), float(b)) for p, s, a, b in meta["spreads"]},
        trim={p: float(t) for p, t in meta.get("trim", {}).items()},
        play_rates={(p, s, bool(t)): float(r) for p, s, t, r in meta.get("play_rates", [])},
    )
    for entry in meta["models"]:
        booster = xgb.Booster()
        booster.load_model(str(directory / entry["file"]))
        out.models[(entry["position"], entry["target"])] = FittedModel(
            entry["position"], targets[entry["target"]], booster, entry["params"],
            entry["trees"], entry["features"], entry["train_seasons"], entry["holdout_score"],
        )  # fmt: skip
    return out
