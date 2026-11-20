"""The machine-learning model graded walk-forward, season by season (ADR-061, ADR-065).

For each test season S the models train on every season from `first` to S-1, and are retrained
before weeks 1, 5, 9 and 13 with S's earlier games added, as the live weekly retrain would have
them (every 4 weeks, not every week, so a full check takes minutes, not hours). Each block of
weeks is projected by the models trained just before it, in every scoring format asked for;
the feature table itself only ever looks at games before each row's kickoff.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pandas as pd

from app.model.ml.features import SKILL
from app.model.ml.project import project
from app.model.ml.train import GRID, TrainingTable, train_all

RETRAIN_WEEKS = (1, 5, 9, 13)  # ADR-065
OUT_COLUMNS = ["gsis_id", "season", "week", "position", "proj"]


def blocks(weeks: Sequence[int], retrain: Sequence[int] = RETRAIN_WEEKS) -> list[list[int]]:
    """Split a season's weeks into the groups each retrain projects: [[1-4], [5-8], ...]."""
    starts = sorted(retrain)
    out: dict[int, list[int]] = {}
    for week in sorted(weeks):
        start = max((s for s in starts if s <= week), default=starts[0])
        out.setdefault(start, []).append(week)
    return list(out.values())


def ml_walk_forward(
    table: TrainingTable,
    first: int,
    seasons: Sequence[int],
    formats: Mapping[str, Mapping[str, float]],
    retrain: Sequence[int] = RETRAIN_WEEKS,
    positions: Sequence[str] = SKILL,
    grid: Sequence[dict[str, Any]] = GRID,
    progress: Callable[[str], None] | None = None,
) -> dict[str, pd.DataFrame]:
    """Projected points for every player-game of `seasons`, one frame per scoring format."""
    parts: dict[str, list[pd.DataFrame]] = {name: [] for name in formats}
    for season in sorted(seasons):
        rows = table.seasons([season])
        weeks = sorted(int(w) for w in rows.features["week"].unique())
        for group in blocks(weeks, retrain):
            models = train_all(
                table, range(first, season), positions, grid, upto=(season, group[0])
            )
            at = (
                rows.features["week"].isin(group) & rows.features["position"].isin(positions)
            ).to_numpy()
            feats = rows.features[at]
            for name, rules in formats.items():
                points = project(models, feats, rules)["points"]
                parts[name].append(feats[OUT_COLUMNS[:-1]].assign(proj=points.to_numpy()))
            if progress:
                progress(f"{season} weeks {group[0]}-{group[-1]}")
    return {name: pd.concat(p, ignore_index=True) for name, p in parts.items()}
