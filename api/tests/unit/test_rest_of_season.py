"""Rest-of-season projections: horizon, playoff weighting, byes, injuries, no leakage."""

import pandas as pd
import pytest

from app.model.rest_of_season import (
    DEFAULT_LAST_FANTASY_WEEK,
    IR_WEEKS,
    PLAYOFF_WEIGHT,
    UNKNOWN_OPPONENT,
    last_fantasy_week,
    project_rest_of_season,
    season_horizon,
    single_week,
)
from tests.unit.test_model import hist


def targets(**extra: object) -> pd.DataFrame:
    return pd.DataFrame([{"gsis_id": "wr1", "position": "WR", "team": "AAA", **extra}])


def steady_history(points: float = 10.0) -> pd.DataFrame:
    """Eight games of `points` against opponents nobody else played (no opponent effect)."""
    return hist([("wr1", 2026, w, "WR", f"Z{w}", points) for w in range(1, 9)])


def every_week_vs(opponent: str, weeks: range) -> dict[int, dict[str, str]]:
    return {w: {"AAA": opponent, opponent: "AAA"} for w in weeks}


# --------------------------------------------------------------------------- horizon
@pytest.mark.parametrize(
    ("start", "teams", "rounds", "last"),
    [
        (15, 6, "one_week", 17),  # 3 rounds (top seeds on bye): weeks 15-17
        (15, 4, "one_week", 16),
        (15, 8, "one_week", 17),
        (14, 4, "two_week_final", 16),  # semifinal 14, final 15-16
        (14, 4, "two_week_rounds", 17),
        (17, 12, "two_week_rounds", 18),  # capped at the NFL's last week
        (None, None, "one_week", DEFAULT_LAST_FANTASY_WEEK),  # no playoffs set
    ],
)
def test_last_fantasy_week(start: int | None, teams: int | None, rounds: str, last: int) -> None:
    assert last_fantasy_week(start, teams, rounds) == last  # type: ignore[arg-type]


def test_horizon_weights_playoff_weeks_more() -> None:
    h = season_horizon(9, 15, 6)
    assert h.weeks == tuple(range(9, 18))
    assert h.playoff_weeks == {15, 16, 17}
    assert h.weights[14] == 1.0 and h.weights[15] == PLAYOFF_WEIGHT
    assert h.total_weight == 6 * 1.0 + 3 * PLAYOFF_WEIGHT


def test_horizon_after_the_season_is_empty() -> None:
    assert season_horizon(18, 15, 6).weeks == ()


# --------------------------------------------------------------------------- projection
def test_total_is_weekly_points_times_weights() -> None:
    h = season_horizon(13, 15, 4)  # weeks 13-16, playoffs 15-16
    out = project_rest_of_season(
        steady_history(), targets(), 2026, h, every_week_vs("BBB", range(13, 17))
    ).iloc[0]
    assert [w["week"] for w in out["weekly"]] == [13, 14, 15, 16]
    assert all(w["points"] == pytest.approx(10.0) for w in out["weekly"])
    assert out["ros_points"] == pytest.approx(10 * (2 + 2 * PLAYOFF_WEIGHT))
    assert out["games"] == 4


def test_bye_week_scores_zero_and_isnt_a_game() -> None:
    schedule = every_week_vs("BBB", range(10, 13))
    schedule[11] = {"CCC": "DDD", "DDD": "CCC"}  # AAA not playing in week 11
    out = project_rest_of_season(
        steady_history(), targets(), 2026, season_horizon(10, None, None), schedule
    ).iloc[0]
    week11 = next(w for w in out["weekly"] if w["week"] == 11)
    assert week11["points"] == 0.0 and week11["opponent"] is None  # not "nan"
    assert out["games"] == len(out["weekly"]) - 1


def test_unloaded_schedule_week_is_a_game_with_no_opponent_adjustment() -> None:
    out = project_rest_of_season(steady_history(), targets(), 2026, single_week(9), {}).iloc[0]
    assert out["weekly"][0]["opponent"] == UNKNOWN_OPPONENT
    assert out["weekly"][0]["points"] == pytest.approx(10.0)
    assert out["games"] == 1


def test_questionable_or_out_only_affects_the_next_game() -> None:
    h = season_horizon(9, 15, 6)
    out = project_rest_of_season(
        steady_history(), targets(injury_status="Out"), 2026, h,
        every_week_vs("BBB", range(9, 18)),
    ).iloc[0]  # fmt: skip
    assert out["weekly"][0]["points"] == 0.0
    assert all(w["points"] == pytest.approx(10.0) for w in out["weekly"][1:])


def test_injured_reserve_lasts_ir_weeks() -> None:
    h = season_horizon(9, 15, 6)
    out = project_rest_of_season(
        steady_history(), targets(injury_status="IR"), 2026, h,
        every_week_vs("BBB", range(9, 18)),
    ).iloc[0]  # fmt: skip
    points = [w["points"] for w in out["weekly"]]
    assert points[:IR_WEEKS] == [0.0] * IR_WEEKS
    assert all(p == pytest.approx(10.0) for p in points[IR_WEEKS:])


def test_future_games_never_leak() -> None:
    """Games at or after the first remaining week must not change the projection."""
    base = steady_history()
    leak = pd.concat([base, hist([("wr1", 2026, w, "WR", "Z", 99.0) for w in range(9, 12)])])
    h = season_horizon(9, None, None)
    schedule = every_week_vs("BBB", range(9, 18))
    a = project_rest_of_season(base, targets(), 2026, h, schedule).iloc[0]["ros_points"]
    b = project_rest_of_season(leak, targets(), 2026, h, schedule).iloc[0]["ros_points"]
    assert a == b


def test_empty_inputs() -> None:
    out = project_rest_of_season(steady_history(), targets().iloc[0:0], 2026, single_week(9), {})
    assert out.empty
    late = season_horizon(18, 15, 6)
    none_left = project_rest_of_season(steady_history(), targets(), 2026, late, {})
    assert none_left.iloc[0]["ros_points"] == 0.0 and none_left.iloc[0]["weekly"] == []
