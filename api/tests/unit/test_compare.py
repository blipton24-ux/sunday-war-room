"""Model comparison, the startable slice and the keep rule (ADR-055); the switches (ADR-054)."""

import numpy as np
import pandas as pd
import pytest

from app.model import compare, metrics
from app.model.config import CANDIDATES, SHIPPED, ModelConfig, by_name
from app.model.projection import Context, project_week

POSITIONS = ("QB", "RB", "WR", "TE")


def frame(
    proj_offset: dict[str, float], seasons=(2024,), weeks=range(1, 13), seed=1
) -> pd.DataFrame:
    """Four players per position per week; projection = actual + a per-position offset + noise."""
    rng = np.random.default_rng(seed)
    rows = []
    for season in seasons:
        for week in weeks:
            for pos in POSITIONS:
                for i in range(4):
                    actual = float(rng.uniform(2, 25))
                    rows.append(
                        {
                            "gsis_id": f"{pos}{i}",
                            "season": season,
                            "week": week,
                            "position": pos,
                            "actual": actual,
                            "naive": actual + float(rng.normal(0, 3)),
                            "injury_flag": None,
                            "proj": actual + proj_offset[pos] + float(rng.normal(0, 0.2)),
                        }
                    )
    return pd.DataFrame(rows)


def flat(offset: float) -> dict[str, float]:
    return dict.fromkeys(POSITIONS, offset)


def paired(base_offset: dict[str, float], cand_offset: dict[str, float], **kw) -> pd.DataFrame:
    base = frame(base_offset, **kw)
    cand = base.copy()
    # the same actuals and baseline picks, a different projection
    rng = np.random.default_rng(2)
    cand["proj"] = (
        cand["actual"] + cand["position"].map(cand_offset) + rng.normal(0, 0.2, len(cand))
    )
    return compare.pair(base, cand)


# --------------------------------------------------------------------------- startable slice
def test_startable_slice_takes_the_top_of_each_position_week_by_the_chosen_column() -> None:
    rows = [
        {"position": "QB", "season": 2025, "week": 1, "naive": float(i), "proj": float(-i)}
        for i in range(20)
    ] + [{"position": "K", "season": 2025, "week": 1, "naive": 1.0, "proj": 1.0}]
    df = pd.DataFrame(rows)
    by_naive = df[metrics.startable_mask(df, "naive")]
    assert len(by_naive) == 15 and by_naive["naive"].min() == 5.0  # top 15 QBs; kickers never
    by_proj = df[metrics.startable_mask(df, "proj")]
    assert len(by_proj) == 15 and by_proj["naive"].max() == 14.0  # a different 15


def test_week_group_splits_the_opener_from_the_season() -> None:
    df = pd.DataFrame({"week": [1, 4, 5, 18]})
    assert metrics.week_group(df).tolist() == ["1-4", "1-4", "5+", "5+"]


# --------------------------------------------------------------------------- pairing
def test_two_models_must_be_graded_on_the_same_player_games() -> None:
    base = frame(flat(0.0))
    with pytest.raises(ValueError, match="exactly the same"):
        compare.pair(base, base.iloc[:-1])


def test_a_model_compared_with_itself_changes_nothing() -> None:
    df = frame(flat(1.0))
    p = compare.pair(df, df)
    d = compare.slice_diff(p, startable=False, weeks=None)
    assert d.change == 0.0 and d.low == 0.0 and d.high == 0.0
    assert not d.better and not d.worse


# --------------------------------------------------------------------------- bootstrap
def test_a_clear_improvement_is_better_beyond_chance() -> None:
    p = paired(flat(3.0), flat(0.0))
    d = compare.slice_diff(p, startable=True, weeks="5+")
    assert d.change < -2.5 and d.better and not d.worse and d.high < 0
    assert d.cand_mae < d.base_mae


def test_a_tiny_random_difference_is_noise() -> None:
    p = paired(flat(1.0), flat(1.0), seed=3)  # same bias, only different noise
    d = compare.slice_diff(p, startable=False, weeks=None)
    assert abs(d.change) < 0.1 and not d.better and not d.worse


def test_injury_games_are_left_out_unless_asked_for() -> None:
    p = paired(flat(0.5), flat(0.5))
    p.loc[p.index[:50], "injury_flag"] = "during"
    p.loc[p.index[50:60], "injury_flag"] = "questionable"
    p["left_out"] = p["injury_flag"].isin(["before", "during"])
    out = compare.slice_diff(p, startable=False, weeks=None)
    counted = compare.slice_diff(p, startable=False, weeks=None, include_injury_games=True)
    assert out.n == counted.n - 50  # questionable games stay in


def test_empty_slice_is_reported_not_crashed() -> None:
    p = paired(flat(0.0), flat(0.0))
    d = compare.slice_diff(p, startable=True, weeks="5+", position="K")
    assert d.n == 0 and np.isnan(d.change)


# --------------------------------------------------------------------------- keep rule
SEASONS_TUNE = (2022, 2023)


def test_an_idea_that_helps_everywhere_is_kept() -> None:
    tune = paired(flat(3.0), flat(0.0), seasons=SEASONS_TUNE)
    check = paired(flat(3.0), flat(0.0), seasons=(2025,), seed=5)
    v = compare.verdict(tune, check)
    assert v.kept and v.reasons == ()


def test_an_idea_that_only_helps_the_tuning_seasons_is_not_kept() -> None:
    tune = paired(flat(3.0), flat(0.0), seasons=SEASONS_TUNE)
    check = paired(flat(1.0), flat(1.0), seasons=(2025,), seed=5)
    v = compare.verdict(tune, check)
    assert not v.kept and any("check season" in r for r in v.reasons)


def test_a_position_made_worse_blocks_the_idea_but_the_helped_ones_are_named() -> None:
    base = {"QB": 3.0, "RB": 3.0, "WR": 3.0, "TE": 0.0}
    cand = {"QB": 0.0, "RB": 0.0, "WR": 0.0, "TE": 1.0}  # TE gets worse by about 1 point
    tune = paired(base, cand, seasons=SEASONS_TUNE)
    check = paired(base, cand, seasons=(2025,), seed=5)
    v = compare.verdict(tune, check)
    assert not v.kept
    assert any("TE" in r and "worse" in r for r in v.reasons)
    assert v.positions_kept == ("QB", "RB", "WR")  # kept for these positions only


def test_the_report_names_both_models_and_the_verdict() -> None:
    tune = paired(flat(3.0), flat(0.0), seasons=SEASONS_TUNE)
    check = paired(flat(3.0), flat(0.0), seasons=(2025,), seed=5)
    text = compare.render("shipped", "idea", tune, check, "Model comparison (full PPR)")
    assert "# Model comparison (full PPR)" in text
    assert "shipped miss" in text and "idea miss" in text
    assert "Tuning seasons (2022, 2023)" in text and "Check season (2025)" in text
    assert "**Kept.**" in text and "| better |" in text
    bad_tune = paired(flat(0.0), flat(3.0), seasons=SEASONS_TUNE)
    bad_check = paired(flat(0.0), flat(3.0), seasons=(2025,), seed=5)
    worse = compare.render("shipped", "idea", bad_tune, bad_check, "t")
    assert "**Not kept.**" in worse and "| worse |" in worse


# --------------------------------------------------------------------------- switches
def test_config_names() -> None:
    assert by_name("shipped") is SHIPPED
    assert CANDIDATES["skip-injury-history"].skip_injury_games_in_history
    assert not SHIPPED.skip_injury_games_in_history  # live code never runs an unproven idea
    with pytest.raises(SystemExit, match="Unknown model config"):
        by_name("nope")


def history_with_a_spoiled_game() -> pd.DataFrame:
    rows = [(2025, w, 10.0, None) for w in range(1, 6)] + [(2025, 6, 0.0, "during")]
    return pd.DataFrame(
        [
            {
                "gsis_id": "wr1",
                "season": s,
                "week": w,
                "position": "WR",
                "team": "AAA",
                "opponent": "KC",
                "points": pts,
                "snap": None,
                "injury_game": flag,
            }
            for s, w, pts, flag in rows
        ]
    )


def test_the_injury_history_switch_leaves_hurt_games_out_of_the_baseline() -> None:
    hist = history_with_a_spoiled_game()
    target = pd.DataFrame([{"gsis_id": "wr1", "position": "WR", "team": "AAA", "opponent": "KC"}])
    ctx = Context(2025, 7)
    shipped = project_week(hist, target, ctx, None)["points"].iloc[0]
    skipping = project_week(hist, target, ctx, None, ModelConfig(skip_injury_games_in_history=True))
    assert skipping["points"].iloc[0] > shipped  # the 0-point injury game no longer drags it down
    # without the column, the switch is harmless
    plain = hist.drop(columns=["injury_game"])
    same = project_week(plain, target, ctx, None, ModelConfig(skip_injury_games_in_history=True))
    assert same["points"].iloc[0] == project_week(plain, target, ctx, None)["points"].iloc[0]
