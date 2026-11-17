"""P4 step 5: labels, the baseline, and training (ADR-061): settings picked inside the training
seasons only, repeatable, saved and loaded without change."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import xgboost as xgb

from app.model.ml import train
from app.model.ml.targets import CATCH_RATE, TARGETS, label, naive
from app.model.ml.train import ModelSet, TrainingTable, fit, load, save, train_all
from app.scripts import train_ml

TINY_GRID = ({"max_depth": 2, "min_child_weight": 1, "colsample_bytree": 1.0},
             {"max_depth": 3, "min_child_weight": 5, "colsample_bytree": 1.0})  # fmt: skip
SEASONS = (2019, 2020, 2021, 2022)


def table(seed: int = 0, n: int = 200) -> TrainingTable:
    """WRs and RBs over four seasons. Targets follow `share` (a planted signal); catches are
    about 60% of targets for everyone."""
    rng = np.random.default_rng(seed)
    rows, stats = [], []
    for season in SEASONS:
        for i in range(n):
            position = "WR" if i % 2 else "RB"
            share = rng.uniform(0.02, 0.3)
            targets = float(rng.poisson(30 * share))
            rows.append({"gsis_id": f"p{i}", "season": season, "week": 1 + i % 17,
                         "position": position, "team": "AAA", "opponent": "BBB",
                         "season_target_share": share, "noise": rng.normal(),
                         "season_targets_pg": np.nan, "last_targets_pg": 5.0,
                         "recent_targets_pg": 4.0, "season_catch_rate": 0.6,
                         "last_catch_rate": np.nan, "recent_catch_rate": np.nan})  # fmt: skip
            carries = float(rng.poisson(2))
            stats.append({"targets": targets, "receptions": float(rng.binomial(int(targets), 0.6)),
                          "carries": carries, "rushing_yards": 4.0 * carries})  # fmt: skip
    features = pd.DataFrame(rows)
    for base in ("carries_pg", "attempts_pg", "yards_per_catch", "rec_td_rate", "yards_per_carry",
                 "rush_td_rate"):  # fmt: skip
        for window in ("season", "last", "recent"):
            features[f"{window}_{base}"] = np.nan  # no history: the report falls back to average
    return TrainingTable(features, pd.DataFrame(stats))


# --------------------------------------------------------------------------- labels
def test_labels_for_counts_and_rates() -> None:
    stats = pd.DataFrame({"targets": [8.0, 0.0, None], "receptions": [6.0, 0.0, 1.0]})
    value, weight = label(stats, TARGETS)
    assert value.tolist() == [8.0, 0.0, 0.0] and weight.tolist() == [1.0, 1.0, 1.0]
    rate, per = label(stats, CATCH_RATE)
    assert rate.iloc[0] == pytest.approx(0.75) and np.isnan(rate.iloc[1])  # no targets: no rate
    assert per.tolist() == [8.0, 0.0, 0.0]  # weighted by targets
    missing, _ = label(stats.drop(columns=["targets"]), TARGETS)
    assert missing.tolist() == [0.0, 0.0, 0.0]


def test_baseline_falls_back_season_then_last_then_recent() -> None:
    f = pd.DataFrame({"season_targets_pg": [6.0, np.nan, np.nan],
                      "last_targets_pg": [9.0, 5.0, np.nan],
                      "recent_targets_pg": [1.0, 1.0, 4.0]})  # fmt: skip
    assert naive(f, TARGETS).tolist() == [6.0, 5.0, 4.0]


# --------------------------------------------------------------------------- training
def test_settings_are_picked_on_the_last_training_season_and_never_see_the_test_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[list[int]] = []
    real = train._matrix

    def spy(feats: pd.DataFrame, *rest: Any) -> xgb.DMatrix:
        seen.append(sorted(feats["season"].unique().tolist()))
        return real(feats, *rest)

    monkeypatch.setattr(train, "_matrix", spy)
    model = fit(table(), "WR", TARGETS, [2019, 2020, 2021], TINY_GRID)
    assert seen == [[2019, 2020], [2021], [2019, 2020, 2021]]  # inner, held back, final
    assert model.train_seasons == [2019, 2020, 2021]
    assert model.params["max_depth"] in (2, 3) and model.trees >= 1
    with pytest.raises(ValueError, match="two seasons"):
        fit(table(), "WR", TARGETS, [2021], TINY_GRID)


def test_the_model_learns_a_planted_signal_and_beats_the_baseline() -> None:
    t = table(n=600)
    models = train_all(t, [2019, 2020, 2021], positions=("WR",), grid=TINY_GRID)
    graded = train_ml.grade(models, t.seasons([2019, 2020, 2021]), t.seasons([2022]))
    targets = graded[graded["target"] == "targets"].iloc[0]
    assert targets["model"] < 0.8 * targets["baseline"]  # the share carries the signal
    assert set(graded["position"]) == {"WR"}  # no RB models were trained


def test_training_is_repeatable() -> None:
    t = table()
    a = fit(t, "WR", TARGETS, [2019, 2020, 2021], TINY_GRID)
    b = fit(t, "WR", TARGETS, [2019, 2020, 2021], TINY_GRID)
    rows = t.seasons([2022]).features
    np.testing.assert_array_equal(a.predict(rows), b.predict(rows))
    assert a.params == b.params and a.trees == b.trees


def test_predictions_go_to_their_own_position_and_survive_save_and_load(tmp_path: Path) -> None:
    t = table()
    models = train_all(t, [2019, 2020, 2021], positions=("WR",), grid=TINY_GRID)
    rows = t.seasons([2022]).features
    out = models.predict(rows)
    wr = (rows["position"] == "WR").to_numpy()
    assert out.loc[wr, "catch_rate"].notna().all() and out.loc[~wr, "catch_rate"].isna().all()
    assert ((out.loc[wr, "catch_rate"] > 0.3) & (out.loc[wr, "catch_rate"] < 0.9)).all()

    save(models, tmp_path)
    back = load(tmp_path)
    assert set(back.models) == set(models.models)
    pd.testing.assert_frame_equal(back.predict(rows), out)
    kept = back.models[("WR", "targets")]
    assert kept.train_seasons == [2019, 2020, 2021] and "season_target_share" in kept.features


def test_report_renders_every_target_and_season() -> None:
    t = table()
    parts = []
    for season in (2021, 2022):
        models = train_all(t, list(range(2019, season)), positions=("WR",), grid=TINY_GRID)
        parts.append(
            train_ml.grade(models, t.seasons(range(2019, season)), t.seasons([season])).assign(
                season=season
            )
        )
    text = train_ml.render(pd.concat(parts, ignore_index=True), 2019, 60.0)
    assert "| WR | targets |" in text and "| WR | catch_rate |" in text
    assert "## Change by test season" in text and "## Settings picked for 2022" in text
    assert "of 2 |" in text


def test_an_empty_model_set_predicts_nothing() -> None:
    rows = table().features.head(3)
    assert ModelSet().predict(rows).empty
