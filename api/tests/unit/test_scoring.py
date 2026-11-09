"""Scoring with a league's own rules. Hand-computed expectations, one per rule shape."""

import pandas as pd
import pytest

from app.model.scoring import check_rules, score, score_one, scoring_key
from tests.sleeper_fixtures import fx

HALF_PPR = fx("league")["scoring_settings"]  # the recorded fixture league's real rules


def test_wide_receiver_half_ppr() -> None:
    # 7 rec, 88 yds, 1 TD, 1 lost fumble: 3.5 + 8.8 + 6 - 2 = 16.3
    stats = {"receptions": 7, "receiving_yards": 88, "receiving_tds": 1,
             "receiving_fumbles_lost": 1}  # fmt: skip
    assert score_one(stats, "WR", HALF_PPR) == pytest.approx(16.3)


def test_te_premium_bonus_only_for_tight_ends() -> None:
    stats = {"receptions": 6, "receiving_yards": 50}
    # rec 0.5 + bonus_rec_te 0.5 per catch for TEs only
    assert score_one(stats, "TE", HALF_PPR) == pytest.approx(6 * 1.0 + 5.0)
    assert score_one(stats, "WR", HALF_PPR) == pytest.approx(6 * 0.5 + 5.0)


def test_quarterback_per_unit() -> None:
    # 280 pass yds @0.04 = 11.2, 2 TD @4 = 8, 1 INT @-1, 30 rush yds = 3  -> 21.2
    stats = {"passing_yards": 280, "passing_tds": 2, "passing_interceptions": 1,
             "rushing_yards": 30}  # fmt: skip
    assert score_one(stats, "QB", HALF_PPR) == pytest.approx(21.2, abs=0.01)


def test_tier_bonus_is_all_or_nothing() -> None:
    rules = {"rec_yd": 0.1, "bonus_rec_yd_100": 3}
    assert score_one({"receiving_yards": 99}, "WR", rules) == pytest.approx(9.9)
    assert score_one({"receiving_yards": 100}, "WR", rules) == pytest.approx(13.0)


@pytest.mark.parametrize(
    ("allowed", "expected"), [(0, 10.0), (6, 7.0), (17, 1.0), (24, 0.0), (31, -1.0), (42, -4.0)]
)
def test_defense_points_allowed_brackets(allowed: int, expected: float) -> None:
    stats = {"points_allowed": allowed}
    assert score_one(stats, "DEF", HALF_PPR) == pytest.approx(expected)


def test_defense_counting_stats() -> None:
    # 3 sacks (1 each) + 1 INT (2) + 1 fumble rec (2 in this league) + 14 allowed (1) = 8
    stats = {"def_sacks": 3, "def_interceptions": 1, "fumble_recovery_opp": 1,
             "points_allowed": 14}  # fmt: skip
    assert score_one(stats, "DEF", HALF_PPR) == pytest.approx(8.0)


def test_offense_rules_do_not_leak_to_defense() -> None:
    assert score_one({"receptions": 5, "points_allowed": 24}, "DEF", HALF_PPR) == 0.0


def test_kicker_distance_buckets() -> None:
    rules = {"fgm_0_19": 3, "fgm_30_39": 3, "fgm_50p": 5, "xpm": 1, "fgmiss": -1}
    stats = {"fg_made_30_39": 1, "fg_made_50_59": 1, "fg_made_60_": 1, "pat_made": 2,
             "fg_missed": 1}  # fmt: skip
    assert score_one(stats, "K", rules) == pytest.approx(3 + 10 + 2 - 1)


def test_unsupported_rules_are_reported_not_dropped() -> None:
    check = check_rules(HALF_PPR)
    # The fixture league scores special-teams fumbles, which nflverse doesn't break out.
    assert set(check.unsupported) == {"def_st_ff", "def_st_fum_rec", "st_ff", "st_fum_rec"}
    assert "fum" not in check.unsupported  # zero-valued: ignored, not "unsupported"


def test_scoring_key_ignores_zero_rules_and_order() -> None:
    a = {"rec": 0.5, "pass_td": 4, "fum": 0}
    b = {"pass_td": 4.0, "rec": 0.5}
    assert scoring_key(a) == scoring_key(b)
    assert scoring_key(a) != scoring_key({"rec": 1, "pass_td": 4})


def test_vectorized_matches_single_rows() -> None:
    df = pd.DataFrame(
        [
            {"position": "WR", "receptions": 5, "receiving_yards": 70},
            {"position": "DEF", "def_sacks": 2, "points_allowed": 10},
            {"position": "QB", "passing_yards": 250, "passing_tds": 2},
        ]
    )
    vec = score(df, HALF_PPR).tolist()
    singles = []
    for r in df.to_dict("records"):
        stats = {str(k): v for k, v in r.items() if k != "position" and pd.notna(v)}
        singles.append(score_one(stats, str(r["position"]), HALF_PPR))
    assert vec == pytest.approx(singles)
