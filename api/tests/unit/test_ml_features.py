"""The P4 feature table (step 4): hand-checked columns on a tiny made-up league, and the leak
test, which changes everything from the projected week on and checks no row moves."""

from datetime import UTC, date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pytest

from app.model.ml.data import ModelData
from app.model.ml.features import TARGET_COLUMNS, build_features, feature_columns

SEASONS = (2024, 2025)
WEEKS = range(1, 7)


def kickoff(season: int, week: int) -> datetime:
    return datetime(season, 9, 8, 17, tzinfo=UTC) + timedelta(days=7 * (week - 1))


def stat(gid: str, pos: str, team: str, season: int, week: int, **s: float) -> dict[str, Any]:
    opp = "BBB" if team == "AAA" else "AAA"
    return {"gsis_id": gid, "season": season, "week": week, "position": pos, "team": team,
            "opponent": opp, "snap": s.pop("snap", 0.8), **s}  # fmt: skip


def league() -> ModelData:
    """AAA plays BBB every week (AAA at home in odd weeks). wr1 gets `week` targets, wr2 4, rb1
    2 targets and 10 carries, qb1 throws to them; BBB has one WR and a QB."""
    rows = []
    for season in SEASONS:
        for week in WEEKS:
            rows += [
                stat("wr1", "WR", "AAA", season, week, targets=week, receptions=week / 2,
                     receiving_yards=10.0 * week, receiving_air_yards=8.0 * week),
                stat("wr2", "WR", "AAA", season, week, targets=4, receptions=3,
                     receiving_yards=30, receiving_air_yards=20),
                stat("rb1", "RB", "AAA", season, week, targets=2, receptions=2,
                     receiving_yards=10, carries=10, rushing_yards=40, rushing_tds=1),
                stat("qb1", "QB", "AAA", season, week, attempts=30, completions=20,
                     passing_yards=250, passing_tds=2, passing_interceptions=1, sacks_suffered=2,
                     carries=3, rushing_yards=12, snap=1.0),
                stat("wr9", "WR", "BBB", season, week, targets=8, receptions=5,
                     receiving_yards=60, receiving_tds=1),
                stat("qb9", "QB", "BBB", season, week, attempts=28, completions=18,
                     passing_yards=200, passing_tds=1, sacks_suffered=3),
            ]  # fmt: skip
    stats = pd.DataFrame(rows)
    games = pd.DataFrame(
        [
            {"season": s, "week": w, "home": "AAA" if w % 2 else "BBB",
             "away": "BBB" if w % 2 else "AAA", "spread_line": 3.0, "total_line": 44.0,
             "home_score": 24, "away_score": 20, "kickoff_at": kickoff(s, w),
             "roof": "dome" if w % 2 else "outdoors"}
            for s in SEASONS for w in WEEKS
        ]
    )  # fmt: skip
    injuries = pd.DataFrame(
        [
            {"gsis_id": "wr1", "season": 2025, "week": 4, "report_status": "Questionable",
             "roster_status": None, "practice_status": "Limited Participation in Practice"},
            {"gsis_id": "wr2", "season": 2025, "week": 4, "report_status": "Out",
             "roster_status": None, "practice_status": "Did Not Participate In Practice"},
        ]
    )  # fmt: skip
    depth = pd.DataFrame(
        [{"gsis_id": "wr1", "season": 2025, "week": 4, "depth_tier": 1},
         {"gsis_id": "wr1", "season": 2025, "week": 5, "depth_tier": 2}]
    )  # fmt: skip
    background = pd.DataFrame(
        [
            {"gsis_id": "wr1", "birth_date": date(2001, 5, 29), "rookie_season": 2023,
             "draft_round": 5, "draft_pick": 177},
            {"gsis_id": "wr2", "birth_date": date(1995, 5, 17), "rookie_season": 2017,
             "draft_round": None, "draft_pick": None},
        ]
    )  # fmt: skip
    return ModelData(stats, games, injuries, depth, background)


def targets(data: ModelData, season: int, week: int) -> pd.DataFrame:
    s = data.stats
    return s[(s["season"] == season) & (s["week"] == week)][list(TARGET_COLUMNS)]


def row(table: pd.DataFrame, gid: str) -> pd.Series:
    return table[table["gsis_id"] == gid].iloc[0]


# --------------------------------------------------------------------------- the leak test
def scrambled_from(data: ModelData, season: int, week: int) -> ModelData:
    """Every outcome at or after (season, week) and every pre-game fact after it, changed."""
    t = data.stats["season"] * 100 + data.stats["week"]
    later = t >= season * 100 + week
    stats = data.stats.copy()
    numeric = [c for c in stats.columns if c not in TARGET_COLUMNS and c != "snap"]
    stats.loc[later, numeric] = stats.loc[later, numeric] * 7 + 3
    stats.loc[later, "snap"] = 0.01
    extra = stats[later].assign(gsis_id="ghost", position="WR")  # a player appearing later
    stats = pd.concat([stats, extra], ignore_index=True)

    games = data.games.copy()
    gt = games["season"] * 100 + games["week"]
    games.loc[gt >= season * 100 + week, ["home_score", "away_score"]] = [99, 0]
    after = gt > season * 100 + week
    games.loc[after, ["spread_line", "total_line"]] = [-20.0, 70.0]
    games.loc[after, "roof"] = "open"

    def later_weeks(df: pd.DataFrame, value: dict[str, Any]) -> pd.DataFrame:
        added = pd.DataFrame(
            [{"gsis_id": g, "season": season, "week": week + 1, **value} for g in ("wr1", "wr2")]
        )
        return pd.concat([df, added], ignore_index=True)

    injuries = later_weeks(data.injuries, {"report_status": "Out", "roster_status": "RES",
                                           "practice_status": None})  # fmt: skip
    depth = later_weeks(data.depth[data.depth["week"] <= week], {"depth_tier": 3})
    return ModelData(stats, games, injuries, depth, data.background)


@pytest.mark.parametrize(("season", "week"), [(2025, 1), (2025, 4), (2025, 6), (2024, 2)])
def test_nothing_from_the_projected_week_on_moves_a_row(season: int, week: int) -> None:
    data = league()
    tg = targets(data, season, week)
    before = build_features(data, tg)
    after = build_features(scrambled_from(data, season, week), tg)
    pd.testing.assert_frame_equal(before, after)


# --------------------------------------------------------------------------- columns
def test_shares_are_ratios_of_totals_with_season_last_and_recent_windows() -> None:
    data = league()
    wr1 = row(build_features(data, targets(data, 2025, 4)), "wr1")
    # weeks 1-3 of 2025: wr1 1+2+3 = 6 targets of the team's 6 + 12 + 6 = 24
    assert wr1["recent_target_share"] == pytest.approx(6 / 24)
    assert wr1["season_target_share"] == pytest.approx(6 / 24)
    assert wr1["season_games"] == 3 and wr1["season_targets"] == 6
    # all of 2024: 21 of 21 + 24 + 12 = 57
    assert wr1["last_target_share"] == pytest.approx(21 / 57)
    assert wr1["last_games"] == 6
    assert wr1["season_catch_rate"] == pytest.approx(0.5)
    assert wr1["season_yards_per_target"] == pytest.approx(10.0)
    assert wr1["season_yards_per_catch"] == pytest.approx(20.0)
    assert wr1["season_air_share"] == pytest.approx(48 / (48 + 60))
    assert wr1["season_snap_share"] == pytest.approx(0.8)
    assert np.isnan(wr1["season_yards_per_attempt"])  # receivers have no pass attempts


def test_week_one_has_no_season_values_and_recent_reaches_back_a_season() -> None:
    data = league()
    wr1 = row(build_features(data, targets(data, 2025, 1)), "wr1")
    assert wr1["season_games"] == 0 and np.isnan(wr1["season_target_share"])
    # recent = 2024 weeks 4-6: 15 of 15 + 12 + 6 = 33
    assert wr1["recent_target_share"] == pytest.approx(15 / 33)
    assert wr1["recent_games"] == 3


def test_quarterback_and_rusher_rates() -> None:
    data = league()
    table = build_features(data, targets(data, 2025, 4))
    qb = row(table, "qb1")
    assert qb["season_completion_rate"] == pytest.approx(20 / 30)
    assert qb["season_yards_per_attempt"] == pytest.approx(250 / 30)
    assert qb["season_int_rate"] == pytest.approx(1 / 30)
    assert qb["season_sack_rate"] == pytest.approx(2 / 32)
    assert qb["season_attempt_share"] == pytest.approx(1.0)
    rb = row(table, "rb1")
    assert rb["season_carry_share"] == pytest.approx(10 / 13)
    assert rb["season_yards_per_carry"] == pytest.approx(4.0)
    assert rb["season_rush_td_rate"] == pytest.approx(0.1)


def test_team_opponent_and_game_context() -> None:
    data = league()
    wr1 = row(build_features(data, targets(data, 2025, 4)), "wr1")
    assert wr1["team_plays_pg_season"] == pytest.approx(30 + 2 + 13)
    assert wr1["team_pass_rate_season"] == pytest.approx(32 / 45)
    assert wr1["team_points_pg_season"] == pytest.approx((24 + 20 + 24) / 3)  # home, road, home
    # BBB has allowed AAA's receivers 1+2+3 + 4*3 targets in three games
    assert wr1["opp_targets_pg_season"] == pytest.approx(18 / 3)
    assert wr1["opp_sack_rate_season"] == pytest.approx(2 / 32)
    # week 4: BBB at home, favoured by 3 -> AAA +3 underdog, implied 20.5 to 23.5
    assert wr1["home"] == 0 and wr1["spread"] == -3.0 and wr1["total"] == 44.0
    assert wr1["implied_team"] == pytest.approx(20.5)
    assert wr1["implied_opponent"] == pytest.approx(23.5)
    assert wr1["dome"] == 0.0 and wr1["rest_days"] == pytest.approx(7.0)
    assert wr1["week_of_season"] == 4 and wr1["early_season"] == 1
    first = row(build_features(data, targets(data, 2025, 1)), "wr1")
    assert np.isnan(first["rest_days"]) and first["dome"] == 1.0


def test_injury_depth_and_teammates_out() -> None:
    data = league()
    table = build_features(data, targets(data, 2025, 4))
    wr1 = row(table, "wr1")
    assert wr1["report_status"] == 1.0 and wr1["practice_status"] == 2.0  # Questionable, Limited
    assert wr1["depth_tier"] == 1.0
    # wr2 is Out in week 4: his season share of AAA targets + carries, 12 of 24 + 39
    assert wr1["out_teammate_share"] == pytest.approx(12 / 63)
    wr2 = row(table, "wr2")
    assert wr2["out_teammate_share"] == 0.0  # never counts himself
    assert row(table, "rb1")["out_teammate_share"] == 0.0  # other positions don't count
    assert row(table, "qb9")["report_status"] == 0.0 and np.isnan(row(table, "qb9")["depth_tier"])


def test_back_from_a_reserve_list() -> None:
    data = league()
    stats = data.stats[~((data.stats["gsis_id"] == "wr1") & data.stats["week"].isin([2, 3])
                         & (data.stats["season"] == 2025))]  # fmt: skip
    reserve = pd.DataFrame(
        [{"gsis_id": "wr1", "season": 2025, "week": 2, "report_status": None,
          "roster_status": "RES", "practice_status": None}]
    )  # fmt: skip
    injuries = pd.concat([data.injuries, reserve], ignore_index=True)
    back = ModelData(stats, data.games, injuries, data.depth, data.background)
    wr1 = row(build_features(back, targets(back, 2025, 4)), "wr1")
    assert wr1["back_from_reserve"] == 1.0 and wr1["weeks_since_last_game"] == 3
    healthy = row(build_features(data, targets(data, 2025, 4)), "wr2")
    assert healthy["back_from_reserve"] == 0.0 and healthy["weeks_since_last_game"] == 1


def test_background() -> None:
    data = league()
    table = build_features(data, targets(data, 2025, 4))
    wr1 = row(table, "wr1")
    played = kickoff(2025, 4).date()
    assert wr1["age"] == pytest.approx((played - date(2001, 5, 29)).days / 365.25)
    assert wr1["years_in_league"] == 2 and wr1["draft_round"] == 5 and wr1["undrafted"] == 0
    assert row(table, "wr2")["undrafted"] == 1.0  # known player, no draft round
    assert np.isnan(row(table, "rb1")["undrafted"])  # no background row: unknown, not undrafted


def test_rows_come_back_in_the_order_given_and_targets_are_checked() -> None:
    data = league()
    tg = targets(data, 2025, 4).iloc[::-1]
    table = build_features(data, tg)
    assert table["gsis_id"].tolist() == tg["gsis_id"].tolist()
    assert len(feature_columns(table)) > 100
    with pytest.raises(ValueError, match="opponent"):
        build_features(data, tg.drop(columns=["opponent"]))


def test_a_live_week_with_no_stats_yet() -> None:
    """The live compute projects a week whose games have not been played."""
    data = league()
    upcoming = pd.DataFrame(
        [{"gsis_id": "wr1", "season": 2025, "week": 7, "position": "WR", "team": "AAA",
          "opponent": "BBB"}]
    )  # fmt: skip
    wr1 = row(build_features(data, upcoming), "wr1")
    assert wr1["season_games"] == 6 and wr1["recent_targets"] == 4 + 5 + 6
    assert np.isnan(wr1["spread"])  # no line stored for week 7 in this league


def test_no_injury_data_at_all() -> None:
    """A fresh database before the first injury load: availability columns are neutral."""
    data = league()
    bare = ModelData(data.stats, data.games, data.injuries.iloc[0:0], data.depth, data.background)
    wr1 = row(build_features(bare, targets(bare, 2025, 4)), "wr1")
    assert wr1["report_status"] == 0.0 and wr1["out_teammate_share"] == 0.0
    assert wr1["back_from_reserve"] == 0.0
