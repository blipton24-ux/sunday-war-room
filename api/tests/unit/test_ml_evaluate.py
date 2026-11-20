"""P4 step 7: the walk-forward with retraining every 4 weeks (ADR-065) and the ship rule's
evidence (ADR-061), on small hand-made frames with known answers."""

import numpy as np
import pandas as pd
import pytest

from app.model import compare
from app.model.ml.project import project
from app.model.ml.targets import TARGETS
from app.model.ml.train import fit, train_all
from app.model.ml.walk_forward import blocks, ml_walk_forward
from tests.unit.test_ml_train import TINY_GRID, table


# --------------------------------------------------------------------------- retraining
def test_blocks_follow_the_retrain_weeks() -> None:
    assert blocks(range(1, 19)) == [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9, 10, 11, 12],
        list(range(13, 19)),
    ]
    assert blocks([3, 4, 9]) == [[3, 4], [9]]  # a season starting late still groups by retrain


def test_before_keeps_only_games_already_played() -> None:
    t = table()
    cut = t.before(2021, 5).features
    assert set(cut["season"]) == {2019, 2020, 2021}
    assert cut.loc[cut["season"] == 2021, "week"].max() == 4
    assert len(t.before(2021, 1).features) == len(t.seasons([2019, 2020]).features)


def test_retraining_adds_this_seasons_weeks_but_keeps_the_settings() -> None:
    t = table()
    plain = fit(t, "WR", TARGETS, [2019, 2020], TINY_GRID)
    week1 = fit(t, "WR", TARGETS, [2019, 2020], TINY_GRID, upto=(2021, 1))
    week9 = fit(t, "WR", TARGETS, [2019, 2020], TINY_GRID, upto=(2021, 9))
    assert week1.trees == plain.trees  # nothing from 2021 is known before its week 1
    assert week9.params == plain.params  # settings come from the held-back 2020 either way
    assert week9.trees >= plain.trees  # more rows support more trees
    rows = t.seasons([2022]).features[lambda f: f["position"] == "WR"]
    assert not np.allclose(week9.predict(rows), plain.predict(rows))


def test_walk_forward_projects_every_test_game_once() -> None:
    t = table()
    out = ml_walk_forward(t, 2019, [2021, 2022], {"ppr": {"rec": 1.0}, "std": {"rec": 0.0}},
                          positions=("WR",), grid=TINY_GRID)  # fmt: skip
    wr = t.features[(t.features["position"] == "WR") & t.features["season"].isin([2021, 2022])]
    for frame in out.values():
        assert len(frame) == len(wr)
        assert not frame.duplicated(["gsis_id", "season", "week"]).any()
        assert list(frame.columns) == ["gsis_id", "season", "week", "position", "proj"]
    assert (out["ppr"]["proj"] >= out["std"]["proj"]).all()  # catches are worth more in PPR
    assert out["ppr"]["proj"].gt(out["std"]["proj"]).any()


def test_walk_forward_matches_one_training_per_block() -> None:
    t = table()
    out = ml_walk_forward(t, 2019, [2022], {"ppr": {"rec": 1.0}}, positions=("WR",),
                          grid=TINY_GRID)["ppr"]  # fmt: skip
    rows = t.seasons([2022]).features
    rows = rows[(rows["position"] == "WR") & rows["week"].between(5, 8)]
    models = train_all(t, [2019, 2020, 2021], ("WR",), TINY_GRID, upto=(2022, 5))

    expected = project(models, rows, {"rec": 1.0})["points"].to_numpy()
    got = out.set_index(["gsis_id", "week"]).loc[
        list(zip(rows["gsis_id"], rows["week"], strict=True)), "proj"
    ]
    assert got.to_numpy() == pytest.approx(expected)


# --------------------------------------------------------------------------- ship evidence
def paired(
    changes: dict[tuple[int, str], float], weeks: int = 6, players: int = 40
) -> pd.DataFrame:
    """A `pair()`-shaped frame: every game the baseline misses by 5, the candidate by 5 + change
    for its season and position, with a little week-to-week noise."""
    rng = np.random.default_rng(1)
    rows = []
    for (season, position), change in changes.items():
        for week in range(1, weeks + 1):
            for i in range(players):
                noise = rng.normal(0, 0.02)
                rows.append({"gsis_id": f"{position}{i}", "season": season, "week": week,
                             "position": position, "actual": 0.0, "proj_base": 5.0,
                             "proj_cand": 5.0 + change + noise, "naive": float(players - i),
                             "injury_flag": None})  # fmt: skip
    df = pd.DataFrame(rows)
    df["startable"] = True
    df["weeks"] = np.where(df["week"] <= 4, "1-4", "5+")
    df["left_out"] = False
    return df


def test_ship_evidence_splits_by_season_and_position() -> None:
    p = paired({(2022, "RB"): -0.2, (2022, "WR"): -0.2, (2023, "RB"): 0.1, (2023, "WR"): -0.3})
    e = compare.ship_evidence(p)
    assert e.pooled.change == pytest.approx(-0.15, abs=0.01) and e.pooled.better
    assert e.seasons[2022].change == pytest.approx(-0.2, abs=0.01)
    assert e.seasons[2023].change == pytest.approx(-0.1, abs=0.01)
    assert e.positions["RB"].change == pytest.approx(-0.05, abs=0.01)
    assert set(e.positions) == {"RB", "WR"} and e.final is None
    final = compare.ship_evidence(p, final=p[p["season"] == 2023]).final
    assert final is not None and final.change == pytest.approx(-0.1, abs=0.01)


# --------------------------------------------------------------------------- ship rule
def evidence(
    seasons: list[float],
    positions: dict[str, float] | None = None,
    final: float | None = 0.0,
    pooled_better: bool = True,
) -> compare.ShipEvidence:
    """Hand-set evidence: a change per season and position, tight intervals around each."""

    def d(change: float, tight: float = 0.01) -> compare.Diff:
        return compare.Diff(1000, 5.0, 5.0 + change, change, change - tight, change + tight)

    pooled = d(-0.1) if pooled_better else d(-0.1, tight=0.2)  # wide: crosses zero
    return compare.ShipEvidence(
        pooled,
        {2022 + i: d(c) for i, c in enumerate(seasons)},
        {p: d(c) for p, c in (positions or {"QB": -0.1, "RB": -0.1}).items()},
        None if final is None else d(final),
    )  # fmt: skip


def test_ship_rule_passes_when_every_condition_holds() -> None:
    v = compare.ship_rule(evidence([-0.2, -0.1, -0.3, 0.05]))  # 3 of 4 is enough
    assert v.kept and v.reasons == ()


@pytest.mark.parametrize(
    ("kw", "reason"),
    [
        ({"pooled_better": False}, "not better beyond chance"),
        ({"seasons": [-0.2, 0.01, 0.02, -0.1]}, "better in only 2 of 4"),
        ({"positions": {"QB": -0.2, "TE": 0.06}}, "TE: worse by 0.060"),
        ({"final": 0.2}, "2026 weeks: change +0.200"),
    ],
)
def test_ship_rule_names_each_failed_condition(kw: dict, reason: str) -> None:
    args = {"seasons": [-0.2, -0.1, -0.3, -0.1], **kw}
    v = compare.ship_rule(evidence(**args))
    assert not v.kept and len(v.reasons) == 1 and reason in v.reasons[0]


def test_a_position_within_the_limit_does_not_block() -> None:
    assert compare.ship_rule(evidence([-0.1] * 4, {"QB": -0.2, "TE": 0.049})).kept


def test_without_the_2026_look_the_test_seasons_decide() -> None:
    assert compare.ship_rule(evidence([-0.1] * 4, final=None)).kept
