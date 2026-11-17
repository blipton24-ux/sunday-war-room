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


@dataclass(frozen=True)
class TrainingTable:
    """`features`: build_features output, one row per player-game. `stats`: the same rows' raw
    stat columns, which the labels come from. Kept apart so a label can never become an input."""

    features: pd.DataFrame
    stats: pd.DataFrame

    def seasons(self, seasons: Sequence[int]) -> TrainingTable:
        keep = self.features["season"].isin(list(seasons)).to_numpy()
        return TrainingTable(
            self.features[keep].reset_index(drop=True), self.stats[keep].reset_index(drop=True)
        )


def training_table(data: ModelData, seasons: Sequence[int]) -> TrainingTable:
    """Every skill-position player-game in `seasons`, with its features and raw stats."""
    s = data.stats
    games = s[s["position"].isin(SKILL) & s["season"].isin(list(seasons))].reset_index(drop=True)
    features = build_features(data, games[list(TARGET_COLUMNS)])
    return TrainingTable(features, games)


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

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        matrix = xgb.DMatrix(features[self.features].astype(float), missing=np.nan)
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
) -> FittedModel:
    """Choose settings on the last training season, then retrain on all of them."""
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

    best: tuple[float, dict[str, Any], int] | None = None
    for settings in grid:
        params = {**BASE_PARAMS, **settings, "objective": objective, "eval_metric": metric}
        booster = xgb.train(
            params, d_inner, num_boost_round=MAX_TREES, evals=[(d_held, "held")],
            early_stopping_rounds=EARLY_STOPPING, verbose_eval=False,
        )  # fmt: skip
        score = float(booster.best_score)
        if best is None or score < best[0]:
            best = (score, params, booster.best_iteration + 1)
    assert best is not None
    score, params, trees = best
    # retrain on every training season; more rows support proportionally more trees
    trees_all = min(MAX_TREES, round(trees * len(y) / max(1, int(inner.sum()))))
    booster = xgb.train(params, _matrix(feats, columns, y, w), num_boost_round=trees_all)
    return FittedModel(position, target, booster, params, trees_all, columns, seasons, score)


@dataclass
class ModelSet:
    """Every fitted model for one training run, keyed by (position, target name)."""

    models: dict[tuple[str, str], FittedModel] = field(default_factory=dict)

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """One column per target name; a row gets values only from its own position's models."""
        out = pd.DataFrame(index=features.index)
        for (position, name), model in self.models.items():
            at = (features["position"] == position).to_numpy()
            if name not in out.columns:
                out[name] = np.nan
            if at.any():
                out.loc[at, name] = model.predict(features[at])
        return out


def train_all(
    table: TrainingTable,
    train_seasons: Sequence[int],
    positions: Sequence[str] = SKILL,
    grid: Sequence[dict[str, Any]] = GRID,
) -> ModelSet:
    out = ModelSet()
    for position in positions:
        for target in BY_POSITION[position]:
            out.models[(position, target.name)] = fit(table, position, target, train_seasons, grid)
    return out


# --------------------------------------------------------------------------- files
META = "models.json"


def save(models: ModelSet, directory: Path) -> None:
    """Each model as XGBoost JSON, plus models.json with its seasons, settings and columns."""
    directory.mkdir(parents=True, exist_ok=True)
    meta: dict[str, Any] = {"xgboost": xgb.__version__, "models": []}
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
    out = ModelSet()
    for entry in meta["models"]:
        booster = xgb.Booster()
        booster.load_model(str(directory / entry["file"]))
        out.models[(entry["position"], entry["target"])] = FittedModel(
            entry["position"], targets[entry["target"]], booster, entry["params"],
            entry["trees"], entry["features"], entry["train_seasons"], entry["holdout_score"],
        )  # fmt: skip
    return out
