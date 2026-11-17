"""P4 step 6: stats, then score (ADR-060, ADR-064). Expected stats, league-average minor stats,
learned spreads, spread-aware scoring of step and bonus rules, and availability."""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import gamma

from app.model.ml import project as proj
from app.model.ml.project import (
    POISSON,
    STATS,
    availability,
    expected_stats,
    fit_minor_rates,
    fit_spreads,
    stat_variance,
)
from app.model.ml.train import ModelSet, TrainingTable
from app.model.scoring import score

# The P4 Build Plan's receiver: 8.1 targets, 66% caught, 12.4 yards a catch, 0.055 TD a target.
PLAN_WR = {"targets": 8.1, "carries": 0.0, "catch_rate": 0.66, "yards_per_catch": 12.4,
           "rec_td_rate": 0.055}  # fmt: skip
FULL_PPR = {"rec": 1.0, "rec_yd": 0.1, "rec_td": 6.0}


def wr(**kw: float) -> pd.DataFrame:
    return pd.DataFrame([{**PLAN_WR, **kw}])


# --------------------------------------------------------------------------- expected stats
def test_the_plan_example_volume_times_rate() -> None:
    out = expected_stats(wr(), pd.Series(["WR"]), {}).iloc[0]
    assert out["receptions"] == pytest.approx(8.1 * 0.66)
    assert out["receiving_yards"] == pytest.approx(8.1 * 0.66 * 12.4)  # about 66
    assert out["receiving_tds"] == pytest.approx(8.1 * 0.055)  # about 0.45
    assert out["attempts"] == 0 and out["passing_yards"] == 0  # receivers have no pass model
    assert set(out.index) == set(STATS)


def test_rates_are_kept_in_range() -> None:
    out = expected_stats(wr(catch_rate=1.3, rec_td_rate=-0.1), pd.Series(["WR"]), {}).iloc[0]
    assert out["receptions"] == pytest.approx(8.1) and out["receiving_tds"] == 0.0


def test_quarterback_stats_and_minor_rates() -> None:
    qb = pd.DataFrame([{"attempts": 30.0, "completion_rate": 0.65, "yards_per_attempt": 7.0,
                        "pass_td_rate": 0.05, "int_rate": 0.02, "carries": 4.0,
                        "yards_per_carry": 5.0, "rush_td_rate": 0.05}])  # fmt: skip
    minor = {("QB", "sacks_suffered"): 0.07, ("QB", "passing_first_downs"): 0.5,
             ("QB", "sack_fumbles_lost"): 0.1, ("QB", "fumbles_total"): 0.02}  # fmt: skip
    out = expected_stats(qb, pd.Series(["QB"]), minor).iloc[0]
    assert out["completions"] == pytest.approx(19.5) and out["passing_yards"] == pytest.approx(210)
    assert out["passing_tds"] == pytest.approx(1.5) and out["rushing_yards"] == pytest.approx(20)
    assert out["sacks_suffered"] == pytest.approx(2.1)  # 30 attempts x league 0.07
    assert out["passing_first_downs"] == pytest.approx(9.75)  # per completion
    assert out["sack_fumbles_lost"] == pytest.approx(0.21)  # per expected sack, set just before
    assert out["fumbles_total"] == pytest.approx(0.02 * (4 + 0 + 2.1))  # carries+catches+sacks


def test_minor_rates_are_league_averages_per_position() -> None:
    features = pd.DataFrame({"position": ["RB", "RB", "WR"]})
    stats = pd.DataFrame(
        {
            "carries": [10.0, 20.0, 0.0],
            "rushing_fumbles_lost": [1.0, 0.0, 0.0],
            "receptions": [2.0, 2.0, 5.0],
            "receiving_first_downs": [1.0, 1.0, 3.0],
        }
    )
    rates = fit_minor_rates(TrainingTable(features, stats))
    assert rates[("RB", "rushing_fumbles_lost")] == pytest.approx(1 / 30)
    assert rates[("RB", "receiving_first_downs")] == pytest.approx(2 / 4)
    assert rates[("WR", "receiving_first_downs")] == pytest.approx(3 / 5)
    assert rates[("WR", "rushing_fumbles_lost")] == 0.0  # no carries at all: zero, not an error


# --------------------------------------------------------------------------- spreads
def test_spreads_recover_a_known_pattern() -> None:
    rng = np.random.default_rng(7)
    mu = rng.uniform(5, 120, 6000)
    var = 2.0 * mu**1.5
    y = rng.gamma(mu**2 / var, var / mu)
    expected = pd.DataFrame({s: 0.0 for s in STATS}, index=range(len(mu))).assign(
        receiving_yards=mu
    )
    actual = pd.DataFrame({"receiving_yards": y})
    spreads = fit_spreads(expected, actual, pd.Series(["WR"] * len(mu)))
    a, b = spreads[("WR", "receiving_yards")]
    assert b == pytest.approx(1.5, abs=0.15) and a == pytest.approx(2.0, rel=0.5)
    assert spreads[("WR", "passing_yards")] == POISSON  # never expected: too little to fit


def test_variance_follows_the_spread_and_is_zero_with_nothing_expected() -> None:
    expected = pd.DataFrame({s: [0.0, 0.0] for s in STATS}).assign(receiving_yards=[0.0, 64.0])
    var = stat_variance(expected, pd.Series(["WR", "WR"]), {("WR", "receiving_yards"): (2.0, 1.5)})
    assert var["receiving_yards"].tolist() == [0.0, pytest.approx(2.0 * 64**1.5)]
    assert var["targets"].tolist() == [0.0, 0.0]


# --------------------------------------------------------------------------- spread-aware scoring
def frame(**stats: float) -> pd.DataFrame:
    return pd.DataFrame([{"position": "WR", **stats}])


def test_no_spread_scores_like_one_game_and_linear_rules_never_change() -> None:
    mean, none = frame(receiving_yards=66.0), frame(receiving_yards=0.0)
    rules = {"espn:REY10": 1.0, "bonus_rec_yd_100": 3.0, "rec_yd": 0.1}
    assert score(mean, rules, none).iloc[0] == score(mean, rules).iloc[0] == pytest.approx(12.6)
    spread = frame(receiving_yards=35.0**2)
    assert score(mean, {"rec_yd": 0.1}, spread).iloc[0] == pytest.approx(6.6)


def test_step_and_bonus_rules_score_their_expected_value() -> None:
    mean, spread = frame(receiving_yards=66.0), frame(receiving_yards=35.0**2)
    k, theta = 66.0**2 / 35.0**2, 35.0**2 / 66.0
    bonus = score(mean, {"bonus_rec_yd_100": 3.0}, spread).iloc[0]
    assert bonus == pytest.approx(3 * gamma.sf(100, k, scale=theta), abs=0.01)  # about 0.47
    games = gamma.rvs(k, scale=theta, size=200_000, random_state=3)
    steps = score(mean, {"espn:REY10": 1.0}, spread).iloc[0]
    assert steps == pytest.approx(np.trunc(games / 10).mean(), abs=0.02)  # about 6.1, not 6


def test_a_range_rule_scores_its_probability() -> None:
    df = pd.DataFrame([{"position": "DEF", "points_allowed": 17.0}])
    spread = pd.DataFrame([{"position": "DEF", "points_allowed": 49.0}])
    k, theta = 17.0**2 / 49.0, 49.0 / 17.0
    expected = gamma.cdf(20, k, scale=theta) - gamma.cdf(14, k, scale=theta)
    got = score(df, {"pts_allow_14_20": 1.0}, spread).iloc[0]
    assert got == pytest.approx(expected, abs=0.01)


# --------------------------------------------------------------------------- availability + points
def test_availability_rules() -> None:
    t = pd.DataFrame(
        {"position": ["WR", "WR", "WR", "WR", "QB", "RB"],
         "injury_status": ["Out", "Questionable", "Doubtful", None, None, None],
         "depth_chart_order": [1, 1, 1, 1, 2, 2]}
    )  # fmt: skip
    assert availability(t).tolist() == [0.0, 0.92, 0.25, 1.0, 0.25, 1.0]  # RB2 not discounted
    assert availability(t[["position"]]).tolist() == [1.0] * 6  # backtests carry no status


def test_points_for_one_league(monkeypatch: pytest.MonkeyPatch) -> None:
    models = ModelSet()
    monkeypatch.setattr(ModelSet, "predict", lambda self, f, inner=False: wr())
    features = pd.DataFrame([{"position": "WR", "injury_status": "Questionable"}])
    out = proj.project(models, features, FULL_PPR).iloc[0]
    full = 8.1 * 0.66 + 8.1 * 0.66 * 12.4 * 0.1 + 8.1 * 0.055 * 6  # 5.35 + 6.63 + 2.67
    assert out["availability"] == 0.92
    assert out["points"] == pytest.approx(round(full * 0.92, 2))
    assert out["exp_receiving_yards"] == pytest.approx(66.29, abs=0.01)
