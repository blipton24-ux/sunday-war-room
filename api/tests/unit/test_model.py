"""Projection model v1, ranges, lineup optimizer, win probability, grading metrics."""

import numpy as np
import pandas as pd
import pytest

from app.model import metrics
from app.model.distribution import (
    Calibration,
    PositionFit,
    apply_range,
    fit_calibration,
    load_calibration,
)
from app.model.lineup import LineupPlayer, optimal_lineup
from app.model.projection import MODEL_VERSION, Context, project_week
from app.model.winprob import SimPlayer, simulate


def hist(
    rows: list[tuple[str, int, int, str, str, float]], snap: float | None = None
) -> pd.DataFrame:
    """rows: (gsis_id, season, week, position, opponent, points)."""
    return pd.DataFrame(
        [
            {"gsis_id": g, "season": s, "week": w, "position": p, "team": "AAA",
             "opponent": o, "points": pts, "snap": snap}
            for g, s, w, p, o, pts in rows
        ]
    )  # fmt: skip


def target(
    gid: str = "wr1", pos: str = "WR", opp: str | None = "KC", **extra: object
) -> pd.DataFrame:
    return pd.DataFrame(
        [{"gsis_id": gid, "position": pos, "team": "AAA", "opponent": opp, **extra}]
    )


def factor(row: pd.Series, name: str) -> dict:  # type: ignore[type-arg]
    return next(f for f in row["factors"] if f["name"] == name)


# --------------------------------------------------------------------------- projection
def test_future_games_never_leak_into_a_projection() -> None:
    base = hist([("wr1", 2026, w, "WR", "X", 10.0) for w in range(1, 5)])
    leak = pd.concat([base, hist([("wr1", 2026, w, "WR", "X", 99.0) for w in range(5, 9)])])
    a = project_week(base, target(), Context(2026, 5), None)
    b = project_week(leak, target(), Context(2026, 5), None)
    assert a["points"].iloc[0] == b["points"].iloc[0]


def test_baseline_blends_this_season_with_last() -> None:
    h = hist(
        [("wr1", 2025, w, "WR", "X", 6.0) for w in range(1, 18)]
        + [("wr1", 2026, w, "WR", "X", 18.0) for w in range(1, 4)]
    )
    row = project_week(h, target(opp="NOPE"), Context(2026, 4), None).iloc[0]
    # 3 games at 18 + prior weight 3 at 6  ->  (3*18 + 3*6) / 6 = 12
    assert factor(row, "baseline")["value"] == pytest.approx(12.0)
    assert "2025 average 6.0" in factor(row, "baseline")["note"]


def test_opponent_factor_is_clamped_and_faded_early() -> None:
    # KC allowed 40/game to WRs over 2 games; league average across opponents is much lower.
    rows = [("wr1", 2026, w, "WR", "Y", 10.0) for w in (1, 2)]
    rows += [(f"o{w}", 2026, w, "WR", "KC", 40.0) for w in (1, 2)]
    rows += [(f"z{w}{i}", 2026, w, "WR", f"T{i}", 10.0) for w in (1, 2) for i in range(8)]
    row = project_week(hist(rows), target(opp="KC"), Context(2026, 3), None).iloc[0]
    opp = factor(row, "opponent")
    # Clamp +25%, faded by 2/(2+4) = 1/3  ->  1 + 0.25/3
    assert opp["value"] == pytest.approx(1 + 0.25 / 3, abs=1e-3)


def test_injury_and_bye() -> None:
    h = hist([("wr1", 2026, w, "WR", "X", 15.0) for w in range(1, 6)])
    out = project_week(h, target(injury_status="Out"), Context(2026, 6), None).iloc[0]
    q = project_week(h, target(injury_status="Questionable"), Context(2026, 6), None).iloc[0]
    bye = project_week(h, target(opp=None), Context(2026, 6), None).iloc[0]
    healthy = project_week(h, target(), Context(2026, 6), None).iloc[0]
    assert out["points"] == 0.0 and factor(out, "injury")["note"] == "Listed Out"
    assert q["points"] == pytest.approx(healthy["points"] * 0.92, abs=0.01)
    assert bye["points"] == 0.0 and factor(bye, "bye")


def test_rookie_without_history_gets_position_prior() -> None:
    h = hist([(f"p{i}", 2025, 1, "RB", "X", float(i)) for i in range(10)])
    row = project_week(h, target("rookie", "RB"), Context(2026, 1), None).iloc[0]
    assert row["points"] == pytest.approx(np.quantile(range(10), 0.30), abs=0.01)
    assert "No NFL history" in factor(row, "baseline")["note"]


def test_defense_projection_may_be_negative() -> None:
    h = hist([("TEAM_X", 2026, w, "DEF", "Y", -3.0) for w in range(1, 5)])
    row = project_week(h, target("TEAM_X", "DEF", "Z"), Context(2026, 5), None).iloc[0]
    assert row["points"] < 0


def test_every_factor_explains_its_effect() -> None:
    h = hist([("wr1", 2026, w, "WR", "X", 12.0) for w in range(1, 6)], snap=0.8)
    row = project_week(h, target(injury_status="Questionable"), Context(2026, 6), None).iloc[0]
    total = sum(f["effect"] for f in row["factors"])
    assert total == pytest.approx(row["points"], abs=0.05)
    assert all(f["note"] for f in row["factors"])


# --------------------------------------------------------------------------- ranges
def test_calibration_file_matches_model_version() -> None:
    cal = load_calibration(MODEL_VERSION)
    assert {"QB", "RB", "WR", "TE", "K", "DEF"} <= set(cal.positions)


def test_fit_recovers_80_percent_coverage_on_synthetic_data() -> None:
    rng = np.random.default_rng(1)
    proj = rng.uniform(2, 25, 5000)
    actual = np.maximum(0, proj + rng.normal(0, 2 + 0.3 * proj))
    df = pd.DataFrame({"position": "WR", "proj": proj, "actual": actual})
    cal = fit_calibration(df, "t", "synthetic")
    ranges = np.array([apply_range(p, "WR", cal) for p in proj])
    inside = (actual >= ranges[:, 0]) & (actual <= ranges[:, 2])
    assert inside.mean() == pytest.approx(0.80, abs=0.02)
    assert (ranges[:, 0] >= 0).all()  # floor learned from data (0 here), not clipped after


def test_range_for_zero_projection_is_zero() -> None:
    cal = Calibration("t", "x", {"WR": PositionFit(2, 0.3, -1.3, 0, 1.3, 0, 100)})
    assert apply_range(0.0, "WR", cal) == (0.0, 0.0, 0.0)


# --------------------------------------------------------------------------- lineup
SLOTS = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "DEF", "BN", "BN", "BN"]


def P(pid: int, pos: str, pts: float, slot: str = "BN", locked: bool = False) -> LineupPlayer:
    return LineupPlayer(pid, pos, pts, slot, locked)


def test_optimal_lineup_fills_flex_with_best_remaining_and_pairs_swaps() -> None:
    roster = [
        P(1, "QB", 20, "QB"), P(2, "RB", 15, "RB"), P(3, "RB", 8, "RB"), P(4, "WR", 14, "WR"),
        P(5, "WR", 9, "WR"), P(6, "TE", 7, "TE"), P(7, "WR", 6, "FLEX"), P(8, "DEF", 5, "DEF"),
        P(9, "RB", 12), P(10, "WR", 11), P(11, "TE", 3),
    ]  # fmt: skip
    res = optimal_lineup(SLOTS, roster)
    starters = {pid for _, pid in res.slots}
    assert starters == {1, 2, 9, 4, 10, 6, 5, 8}
    assert res.optimal_points == pytest.approx(20 + 15 + 12 + 14 + 11 + 7 + 9 + 5)
    # Each incoming starter replaces a specific current starter.
    assert {(s.player_in, s.player_out) for s in res.swaps} == {(9, 7), (10, 3)}
    assert all(s.gain > 0 for s in res.swaps)


def test_overlapping_flex_where_greedy_would_be_wrong() -> None:
    """REC_FLEX takes WR/TE, WRRB_FLEX takes WR/RB. Best: TE->REC, WR->WRRB (30)."""
    slots = ["WRRB_FLEX", "REC_FLEX", "BN", "BN"]
    roster = [P(1, "WR", 20), P(2, "TE", 10), P(3, "RB", 5)]
    res = optimal_lineup(slots, roster)
    assert dict(res.slots) == {"WRRB_FLEX": 1, "REC_FLEX": 2}
    assert res.optimal_points == 30


def test_locked_players_stay_put() -> None:
    roster = [P(1, "QB", 2, "QB", locked=True), P(2, "QB", 25)]
    res = optimal_lineup(["QB", "BN"], roster)
    assert res.slots == [("QB", 1)] and res.swaps == []


def test_ir_players_are_never_started() -> None:
    res = optimal_lineup(["RB", "BN"], [P(1, "RB", 30, "IR"), P(2, "RB", 5, "BN")])
    assert res.slots == [("RB", 2)]


# --------------------------------------------------------------------------- win probability
def test_win_probability_sane_and_deterministic() -> None:
    even = [SimPlayer(8, 12, 18)] * 9
    r1 = simulate(even, even)
    assert r1.win_prob == pytest.approx(0.5, abs=0.02)
    assert simulate(even, even) == r1  # seeded: no flicker between refreshes
    strong = [SimPlayer(12, 16, 22)] * 9
    assert simulate(strong, even).win_prob > 0.9
    assert simulate(strong, even).my_median > simulate(strong, even).opp_median


def test_finished_games_are_fixed_points() -> None:
    done_mine = [SimPlayer(30, 30, 30)]
    done_theirs = [SimPlayer(10, 10, 10)]
    assert simulate(done_mine, done_theirs).win_prob == 1.0


# --------------------------------------------------------------------------- metrics
def test_grade_definitions() -> None:
    df = pd.DataFrame(
        {"position": "WR", "season": 2025, "week": 1,
         "proj": [10.0, 12.0, 4.0, 20.0, 7.0], "actual": [12.0, 10.0, 4.0, 26.0, 1.0],
         "p10": [5.0, 6.0, 1.0, 12.0, 3.0], "p90": [15.0, 18.0, 8.0, 25.0, 12.0]}
    )  # fmt: skip
    g = metrics.grade(df)
    assert g["mae"] == pytest.approx((2 + 2 + 0 + 6 + 6) / 5)
    assert g["bias"] == pytest.approx((-2 + 2 + 0 - 6 + 6) / 5)
    assert g["coverage_80"] == pytest.approx(3 / 5)
    # ranks proj [3,4,1,5,2] vs actual [4,3,2,5,1]: sum d^2 = 4 -> 1 - 6*4/(5*24) = 0.8
    assert g["rank_corr"] == pytest.approx(0.8)
