"""The P4 model ideas (ADR-054): feature functions, the switches and per-position settings.

Every feature is checked for the one thing a backtest cannot survive: reading a game at or after
the week being projected.
"""

from typing import Any

import nflreadpy
import numpy as np
import pandas as pd
import polars as pl
import pytest

from app.model import compare
from app.model.config import SHIPPED, ModelConfig, by_name
from app.model.features import defense, opportunity
from app.model.features.context import LEAGUE_POINTS, Extras, build_extras, is_dome
from app.model.projection import RAW_COLUMNS, Context, project_week
from app.services.history import scored_history
from app.sources import nflverse
from tests.unit.test_compare import flat, paired


def games(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """History rows with every raw stat column present (0 unless given)."""
    base: dict[str, Any] = {
        "season": 2025, "position": "WR", "team": "AAA", "opponent": "X", "points": 0.0,
        "snap": None,
    } | dict.fromkeys(RAW_COLUMNS, 0.0)  # fmt: skip
    return pd.DataFrame([base | r for r in rows])


def target(gid: str = "wr1", pos: str = "WR", opp: str | None = "KC", team: str = "AAA") -> Any:
    return pd.DataFrame([{"gsis_id": gid, "position": pos, "team": team, "opponent": opp}])


def factor(row: pd.Series, name: str) -> dict[str, Any]:  # type: ignore[type-arg]
    found: dict[str, Any] = next(f for f in row["factors"] if f["name"] == name)
    return found


def has(row: pd.Series, name: str) -> bool:  # type: ignore[type-arg]
    return any(f["name"] == name for f in row["factors"])


def one(
    history: pd.DataFrame,
    tgt: pd.DataFrame,
    config: ModelConfig,
    extras: Extras | None = None,
    week: int = 6,
) -> pd.Series:  # type: ignore[type-arg]
    return project_week(history, tgt, Context(2025, week), None, config, extras).iloc[0]


# --------------------------------------------------------------------------- opportunity
def volume_seasons(points_2025: float = 0.0) -> pd.DataFrame:
    """2024: WR points are exactly 1.5 per target + 0.5 per carry, one touchdown every 10
    targets. 2025: whatever the caller says (it must never reach a fit made for 2025)."""
    rng = np.random.default_rng(3)
    rows = []
    for i in range(250):
        tgts, carries = float(rng.integers(1, 12)), float(rng.integers(0, 3))
        rows.append(
            {"gsis_id": f"p{i % 25}", "season": 2024, "week": 1 + i % 17, "targets": tgts,
             "carries": carries, "points": 1.5 * tgts + 0.5 * carries,
             "receiving_tds": tgts / 10.0}
        )  # fmt: skip
    rows += [
        {"gsis_id": f"p{i}", "season": 2025, "week": 1, "targets": 5.0, "points": points_2025}
        for i in range(25)
    ]
    return games(rows)


def test_expected_points_are_fit_on_earlier_seasons_only() -> None:
    fit = opportunity.fit_opportunity(volume_seasons(), before_season=2025)["WR"]
    assert fit.weights == pytest.approx((1.5, 0.5))
    wild = opportunity.fit_opportunity(volume_seasons(points_2025=500.0), before_season=2025)
    assert wild["WR"] == fit  # the 2025 games changed and the fit did not
    assert "QB" not in wild  # too few games to fit: the position is left alone


def test_expected_points_come_from_volume_alone() -> None:
    fits = opportunity.fit_opportunity(volume_seasons(), 2025)
    df = games(
        [
            {"gsis_id": "a", "week": 1, "targets": 10.0, "carries": 2.0, "points": 2.0},
            {"gsis_id": "k", "week": 1, "position": "K", "points": 9.0},
        ]
    )
    xfp = opportunity.expected_points(df, fits)
    assert xfp.iloc[0] == pytest.approx(16.0)  # 10 targets and 2 carries, whatever he scored
    assert np.isnan(xfp.iloc[1])


def test_touchdown_regression_replaces_lucky_touchdowns_with_the_usual_rate() -> None:
    fits = opportunity.fit_opportunity(volume_seasons(), 2025)
    rate = fits["WR"].td_per_opportunity
    df = games([{"gsis_id": "a", "week": 1, "targets": 10.0, "points": 27.0, "receiving_tds": 3.0}])
    assert opportunity.regress_touchdowns(df, fits, 0.0).iloc[0] == 27.0
    full = opportunity.regress_touchdowns(df, fits, 1.0).iloc[0]
    assert full == pytest.approx(27.0 - 18.0 + rate * 10.0)
    half = opportunity.regress_touchdowns(df, fits, 0.5).iloc[0]
    assert half == pytest.approx((27.0 + full) / 2)


def test_usage_share_is_a_players_part_of_his_teams_targets_and_carries() -> None:
    df = games(
        [
            {"gsis_id": "a", "week": 1, "targets": 6.0},
            {"gsis_id": "b", "week": 1, "position": "RB", "carries": 14.0},
            {"gsis_id": "q", "week": 1, "position": "QB", "carries": 4.0},
            {"gsis_id": "c", "week": 2, "team": "BBB"},
        ]
    )
    share = opportunity.usage_share(df)
    assert share.iloc[0] == pytest.approx(0.25) and share.iloc[1] == pytest.approx(14 / 24)
    assert np.isnan(share.iloc[2])  # quarterbacks have no role factor
    assert np.isnan(share.iloc[3])  # a team with no recorded opportunities


# --------------------------------------------------------------------------- defense
def defense_games() -> pd.DataFrame:
    """KC is soft against the pass and stout against the run; the other six teams are average."""
    rows = []
    for week in (1, 2, 3):
        for opp in ("KC", "T1", "T2", "T3", "T4", "T5", "T6"):
            soft = opp == "KC"
            rows.append(
                {"gsis_id": f"w{opp}{week}", "week": week, "opponent": opp, "position": "WR",
                 "receiving_yards": 200.0 if soft else 100.0, "rushing_yards": 5.0,
                 "points": 20.0 if soft else 10.0}
            )  # fmt: skip
            rows.append(
                {"gsis_id": f"r{opp}{week}", "week": week, "opponent": opp, "position": "RB",
                 "rushing_yards": 50.0 if soft else 100.0, "receiving_yards": 40.0,
                 "points": 13.0 if soft else 14.0}
            )  # fmt: skip
    return games(rows)


def test_allowed_tables_split_passing_from_rushing() -> None:
    allowed = defense.build_allowed(defense_games(), ("QB", "RB", "WR", "TE"))
    assert allowed.games[("KC", "WR")] == 3
    assert allowed.passing[("KC", "WR")] == pytest.approx(20.0)
    assert allowed.running[("KC", "RB")] == pytest.approx(5.0)
    passing = defense.ratio(allowed.passing, allowed.league_passing, ("KC", "WR"))
    running = defense.ratio(allowed.running, allowed.league_running, ("KC", "RB"))
    assert passing is not None and passing > 1.5
    assert running is not None and running < 0.6
    assert defense.ratio(allowed.passing, allowed.league_passing, ("NOPE", "WR")) is None
    assert defense.ratio({("KC", "K"): 1.0}, {"K": 0.0}, ("KC", "K")) is None  # no average


def test_pass_share_is_the_players_own_once_he_has_three_games() -> None:
    few = games([{"gsis_id": "a", "week": w, "rushing_yards": 100.0} for w in (1, 2)])
    assert defense.pass_share(few, "RB") == defense.DEFAULT_PASS_SHARE["RB"]
    assert defense.pass_share(None, "WR") == 1.0
    runner = games(
        [{"gsis_id": "a", "week": w, "rushing_yards": 90.0, "receiving_yards": 10.0}
         for w in (1, 2, 3)]
    )  # fmt: skip
    assert defense.pass_share(runner, "RB") == pytest.approx(0.1)
    idle = games([{"gsis_id": "a", "week": w} for w in (1, 2, 3)])
    assert defense.pass_share(idle, "RB") == defense.DEFAULT_PASS_SHARE["RB"]


def test_the_split_opponent_factor_moves_runners_and_receivers_apart() -> None:
    hist = pd.concat(
        [
            defense_games(),
            games(
                [{"gsis_id": "wr1", "week": w, "opponent": "Z", "points": 10.0,
                  "receiving_yards": 100.0} for w in (1, 2, 3)]
                + [{"gsis_id": "rb1", "week": w, "opponent": "Z", "position": "RB",
                    "points": 10.0, "rushing_yards": 100.0} for w in (1, 2, 3)]
            ),
        ]
    )  # fmt: skip
    split = ModelConfig(def_pass=True, def_run=True)
    wr = factor(one(hist, target("wr1"), split, week=4), "opponent")
    rb = factor(one(hist, target("rb1", "RB"), split, week=4), "opponent")
    assert wr["value"] > 1.05 and "passing game 100% of his points" in wr["note"]
    assert rb["value"] < 0.95  # a pure runner against a defense that stops the run
    # the shipped factor only sees total points allowed to running backs
    shipped_rb = factor(one(hist, target("rb1", "RB"), SHIPPED, week=4), "opponent")
    assert rb["value"] < shipped_rb["value"]
    unknown = factor(one(hist, target("wr1", opp="NOPE"), split, week=4), "opponent")
    assert unknown["value"] == 1.0


def test_schedule_adjustment_rates_a_defense_against_its_opponents_own_averages() -> None:
    # KC allowed 20 to a receiver who averages 20 everywhere: nothing special about KC.
    rows = [{"gsis_id": "star", "week": w, "opponent": o, "points": 20.0}
            for w, o in ((1, "KC"), (2, "T1"), (3, "T2"))]  # fmt: skip
    rows += [{"gsis_id": f"j{w}", "week": w, "opponent": o, "points": 6.0}
             for w, o in ((1, "T1"), (2, "T2"), (3, "T3"))]  # fmt: skip
    rows += [{"gsis_id": "wr1", "week": w, "opponent": "Z", "points": 10.0} for w in (1, 2, 3)]
    hist = games(rows)
    plain = factor(one(hist, target(), SHIPPED, week=4), "opponent")
    adjusted = factor(
        one(hist, target(), ModelConfig(def_schedule_adjust=True), week=4), "opponent"
    )
    assert plain["value"] > 1.0  # raw points allowed make KC look soft
    assert adjusted["value"] == pytest.approx(1.0)


def test_pressure_factor_lowers_a_quarterback_against_a_defense_that_gets_home() -> None:
    rows = [{"gsis_id": "qb1", "week": w, "position": "QB", "opponent": "Z", "points": 20.0}
            for w in (1, 2, 3)]  # fmt: skip
    for team, sacks in (("KC", 6.0), ("T1", 2.0), ("T2", 2.0), ("T3", 2.0)):
        rows += [{"gsis_id": team, "week": w, "position": "DEF", "team": team,
                  "def_sacks": sacks, "def_interceptions": 1.0} for w in (1, 2, 3)]  # fmt: skip
    hist = games(rows)
    cfg = ModelConfig(def_sack_int=0.3)
    hard = factor(one(hist, target("qb1", "QB", "KC"), cfg, week=4), "pressure")
    easy = factor(one(hist, target("qb1", "QB", "T1"), cfg, week=4), "pressure")
    assert 0.9 <= hard["value"] < 1.0 < easy["value"]
    assert not has(one(hist, target("qb1", "QB", "KC"), SHIPPED, week=4), "pressure")
    assert not has(one(hist, target("wr1", "WR", "KC"), cfg, week=4), "pressure")


# --------------------------------------------------------------------------- game context
def schedule(week3_score: float = 20.0) -> pd.DataFrame:
    rows = []
    for season in (2024, 2025):
        for week in (1, 2, 3, 4):
            for team, opp, pts, implied, spread in (
                ("AAA", "KC", 30.0, 27.0, 6.5),
                ("KC", "AAA", 10.0, 20.5, -6.5),
            ):
                scored = week3_score if (season, week, team) == (2025, 3, "AAA") else pts
                rows.append(
                    {"season": season, "week": week, "team": team, "opponent": opp,
                     "home": team == "AAA", "spread": spread, "implied": implied,
                     "total": 47.5, "roof": "outdoors", "temp": 50.0, "wind": 22.0,
                     "rest": 7.0, "points_for": scored, "points_against": 0.0}
                )  # fmt: skip
    return pd.DataFrame(rows)


def test_team_strength_and_the_league_line_only_read_earlier_games() -> None:
    a, b = build_extras(schedule()), build_extras(schedule(week3_score=70.0))
    assert a.strength[("AAA", 2025, 3)] == b.strength[("AAA", 2025, 3)]
    assert a.strength[("AAA", 2025, 4)] < b.strength[("AAA", 2025, 4)]
    assert a.strength[("AAA", 2025, 1)] > 1.0 > a.strength[("KC", 2025, 1)]  # last season
    assert a.league_implied[(2024, 1)] == LEAGUE_POINTS  # nothing earlier to average
    assert a.league_implied[(2025, 3)] == pytest.approx(23.75)
    assert a.game("AAA", 2025, 3)["implied"] == 27.0 and a.game("NOPE", 2025, 3) is None
    assert a.draft == {}


def test_dome_and_closed_roofs_count_as_indoors() -> None:
    assert is_dome("dome") and is_dome("Closed")
    assert not is_dome("outdoors") and not is_dome(None)


def steady(pos: str = "WR", gid: str = "wr1", team: str = "AAA") -> pd.DataFrame:
    return games(
        [{"gsis_id": gid, "week": w, "position": pos, "team": team, "points": 10.0}
         for w in (1, 2, 3)]
    )  # fmt: skip


def test_market_and_team_strength_raise_a_player_on_a_team_expected_to_score() -> None:
    extras = build_extras(schedule())
    row = one(steady(), target(), ModelConfig(implied_total=0.6, team_offense=0.5), extras, 4)
    implied, offense = factor(row, "implied total"), factor(row, "team offense")
    assert implied["value"] == pytest.approx(1 + 0.6 * (27 / 23.75 - 1), abs=1e-3)
    assert offense["value"] > 1.0
    assert row["points"] > 10.0
    underdog = one(
        steady(team="KC"), target(team="KC", opp="AAA"), ModelConfig(implied_total=0.6), extras, 4
    )
    assert underdog["points"] < 10.0


def test_game_script_moves_runners_and_receivers_in_opposite_directions() -> None:
    extras, cfg = build_extras(schedule()), ModelConfig(game_script=0.01)
    rb = factor(one(steady("RB", "rb1"), target("rb1", "RB"), cfg, extras, 4), "game script")
    wr = factor(one(steady(), target(), cfg, extras, 4), "game script")
    assert rb["value"] == pytest.approx(1.065) and wr["value"] == pytest.approx(
        1 - 0.0325, abs=1e-3
    )
    assert "favoured by 6.5" in rb["note"]


def test_venue_wind_and_rest() -> None:
    cfg = ModelConfig(home_boost=0.03, wind_penalty=0.05, rest_effect=0.04)
    extras = build_extras(schedule())
    home = one(steady(), target(), cfg, extras, 4)
    away = one(steady(team="KC"), target(team="KC", opp="AAA"), cfg, extras, 4)
    assert factor(home, "venue")["value"] == 1.03 and factor(away, "venue")["value"] == 0.97
    assert factor(home, "weather")["value"] == pytest.approx(0.9)  # 22 mph
    assert not has(home, "rest")  # a normal week
    rb = one(steady("RB", "rb1"), target("rb1", "RB"), cfg, extras, 4)
    assert not has(rb, "weather")  # wind is a passing and kicking effect

    indoors = schedule().assign(roof="dome")
    assert not has(one(steady(), target(), cfg, build_extras(indoors), 4), "weather")
    short = one(steady(), target(), cfg, build_extras(schedule().assign(rest=4.0)), 4)
    long = one(steady(), target(), cfg, build_extras(schedule().assign(rest=13.0)), 4)
    assert factor(short, "rest")["value"] == 0.96 and factor(long, "rest")["value"] == 1.04


def test_kickers_follow_their_team_and_defenses_the_other_team() -> None:
    extras = build_extras(schedule())
    k = one(steady("K", "k1"), target("k1", "K"), ModelConfig(kicker_model=1.0), extras, 4)
    assert factor(k, "team scoring")["value"] == pytest.approx(27 / 23.75, abs=1e-3)
    cfg = ModelConfig(defense_model=1.0)
    easy = one(steady("DEF", "AAA"), target("AAA", "DEF"), cfg, extras, 4)
    hard = one(steady("DEF", "KC", "KC"), target("KC", "DEF", "AAA", "KC"), cfg, extras, 4)
    assert factor(easy, "opposing offense")["value"] > 1.0
    assert factor(hard, "opposing offense")["value"] < 1.0


def test_context_switches_do_nothing_without_a_game_or_without_extras() -> None:
    cfg = ModelConfig(implied_total=0.6, home_boost=0.03)
    extras = build_extras(schedule())
    unknown = one(steady(team="ZZZ"), target(team="ZZZ"), cfg, extras, 4)
    assert [f["name"] for f in unknown["factors"]] == ["baseline", "opponent"]
    assert one(steady(), target(), cfg, None, 4)["points"] == 10.0


def test_a_rookie_starts_where_recent_rookies_from_his_round_did() -> None:
    rows = [{"gsis_id": f"old{i}", "season": 2024, "week": w, "points": 4.0}
            for i in range(10) for w in (1, 2)]  # fmt: skip
    rows += [{"gsis_id": "r24", "season": 2024, "week": w, "points": 13.0} for w in (1, 2, 3)]
    hist = games(rows)
    draft = pd.DataFrame(
        {"gsis_id": ["r24", "new", "late"], "draft_year": [2024, 2025, 2025], "round": [1, 1, 7]}
    )
    extras = build_extras(schedule(), draft)
    cfg = ModelConfig(rookie_prior=True)
    first = one(hist, target("new"), cfg, extras, 1)
    assert factor(first, "baseline")["value"] == 13.0
    assert "Rookie drafted in round 1" in factor(first, "baseline")["note"]
    assert ("rookie", 2025) in extras.cache  # fitted once per season, then reused
    again = one(hist, target("new"), cfg, extras, 1)
    assert again["points"] == first["points"]
    # no comparable earlier rookies, or not a rookie at all: the usual low starting value
    low = factor(one(hist, target("new"), SHIPPED, extras, 1), "baseline")["value"]
    assert factor(one(hist, target("late"), cfg, extras, 1), "baseline")["value"] == low
    assert factor(one(hist, target("undrafted"), cfg, extras, 1), "baseline")["value"] == low


# --------------------------------------------------------------------------- baseline ideas
def busy_but_unlucky() -> pd.DataFrame:
    """A 2025 receiver seeing 12 targets a game and scoring only 6 points from them."""
    mine = games([{"gsis_id": "wr1", "week": w, "targets": 12.0, "points": 6.0} for w in (1, 2, 3)])
    return pd.concat([volume_seasons().query("season == 2024"), mine])


def test_volume_blend_raises_a_player_whose_opportunities_outrun_his_points() -> None:
    hist = busy_but_unlucky()
    tgt = target(opp="NOPE")
    shipped = one(hist, tgt, SHIPPED, week=4)
    blended = one(hist, tgt, ModelConfig(xfp_weight=0.5), week=4)
    assert blended["points"] > shipped["points"]
    assert "50% from volume" in factor(blended, "baseline")["note"]
    full = one(hist, tgt, ModelConfig(xfp_weight=1.0), week=4)
    assert full["points"] > blended["points"]
    # the fit is cached on the extras object and gives the same answer
    extras = build_extras(schedule())
    cached = [one(hist, tgt, ModelConfig(xfp_weight=0.5), extras, 4)["points"] for _ in (1, 2)]
    assert cached == [blended["points"]] * 2 and ("opportunity", 2025) in extras.cache


def test_touchdown_regression_lowers_a_player_living_on_touchdowns() -> None:
    lucky = games(
        [{"gsis_id": "wr1", "week": w, "targets": 3.0, "points": 16.0, "receiving_tds": 2.0}
         for w in (1, 2, 3)]
    )  # fmt: skip
    hist = pd.concat([volume_seasons().query("season == 2024"), lucky])
    tgt = target(opp="NOPE")
    shipped = one(hist, tgt, SHIPPED, week=4)["points"]
    assert one(hist, tgt, ModelConfig(td_regression=0.5), week=4)["points"] < shipped


def test_usage_trend_replaces_the_snap_share_role_factor() -> None:
    rows = []
    for week, mine in ((1, 4.0), (2, 4.0), (3, 4.0), (4, 10.0), (5, 10.0)):
        rows.append({"gsis_id": "wr1", "week": week, "targets": mine, "points": 10.0, "snap": 0.8})
        rows.append({"gsis_id": "wr2", "week": week, "targets": 20.0 - mine, "points": 10.0})
    hist = games(rows)
    trend = factor(one(hist, target(opp="NOPE"), ModelConfig(usage_trend=True)), "role")
    assert trend["value"] == pytest.approx(1.15)  # clamped
    assert "Share of team targets and carries" in trend["note"]
    snaps = factor(one(hist, target(opp="NOPE"), SHIPPED), "role")
    assert snaps["value"] == 1.0  # his snap share never moved
    wide = ModelConfig(usage_trend=True, role_clamp=0.5, role_window=1)
    assert factor(one(hist, target(opp="NOPE"), wide), "role")["value"] > 1.15
    idle = games([{"gsis_id": "wr1", "week": w, "points": 5.0} for w in (1, 2, 3)])
    assert not has(one(idle, target(opp="NOPE"), ModelConfig(usage_trend=True), week=4), "role")


def test_no_idea_reads_the_week_being_projected_or_later() -> None:
    """Every switch on at once: games from the target week on must not move the number."""
    cfg = ModelConfig(
        xfp_weight=0.5, td_regression=0.5, usage_trend=True, def_pass=True, def_run=True,
        def_schedule_adjust=True, def_sack_int=0.3, half_life=6.0, prior_games=5.0,
    )  # fmt: skip
    past = pd.concat([busy_but_unlucky(), defense_games()])
    future = games(
        [{"gsis_id": g, "week": w, "opponent": "KC", "targets": 30.0, "points": 60.0,
          "receiving_yards": 400.0, "receiving_tds": 3.0}
         for g in ("wr1", "other") for w in (4, 5, 6)]
    )  # fmt: skip
    a = one(past, target(), cfg, week=4)
    b = one(pd.concat([past, future]), target(), cfg, week=4)
    assert a["points"] == b["points"] and a["factors"] == b["factors"]


# --------------------------------------------------------------------------- settings
def test_settings_are_parsed_from_names_values_and_positions() -> None:
    cfg = by_name("xfp_weight=0.5@WR/TE+implied-total+usage_trend=true@RB+role_window=3")
    assert cfg.implied_total == 0.6 and cfg.role_window == 3 and cfg.xfp_weight == 0.0
    assert cfg.for_position("WR").xfp_weight == 0.5 == cfg.for_position("TE").xfp_weight
    assert cfg.for_position("QB").xfp_weight == 0.0
    assert cfg.for_position("RB").usage_trend and not cfg.for_position("WR").usage_trend
    assert cfg.for_position("WR").overrides == ()
    assert by_name("prior_games_opener=none").prior_games_opener is None
    assert by_name("td-regression@QB").for_position("QB").td_regression == 0.5
    with pytest.raises(SystemExit, match="Unknown model setting"):
        by_name("nope=1")
    with pytest.raises(SystemExit, match="Unknown model setting"):
        by_name("overrides=1")


def test_overrides_for_one_position_stack_instead_of_replacing() -> None:
    cfg = SHIPPED.with_override(("WR",), {"xfp_weight": 0.5}).with_override(
        ("WR", "TE"), {"half_life": 6.0}
    )
    wr = cfg.for_position("WR")
    assert (wr.xfp_weight, wr.half_life) == (0.5, 6.0)
    assert (cfg.for_position("TE").xfp_weight, cfg.for_position("TE").half_life) == (0.0, 6.0)
    assert hash(cfg) == hash(cfg.with_override(("TE",), {"half_life": 6.0}))  # usable as a key


def test_settings_know_which_data_they_need() -> None:
    assert not SHIPPED.needs_extras and not SHIPPED.needs_raw_stats
    assert ModelConfig(kicker_model=0.3).needs_extras
    assert ModelConfig(def_pass=True).needs_raw_stats
    assert not ModelConfig(half_life=9.0).needs_extras


def test_memory_settings_by_position_and_for_the_opening_weeks() -> None:
    cfg = ModelConfig(
        prior_games_opener=6.0,
        half_life_by_position=(("QB", 9.0),),
        prior_games_by_position=(("QB", 5.0),),
    )
    assert cfg.half_life_for("QB") == 9.0 and cfg.half_life_for("WR") == 4.0
    assert cfg.prior_games_for("QB", 3) == 6.0  # weeks 1-4 use the opener weight
    assert cfg.prior_games_for("QB", 5) == 5.0 and cfg.prior_games_for("WR", 5) == 3.0


def test_each_position_runs_with_its_own_settings_and_rows_keep_their_order() -> None:
    hist = pd.concat(
        [
            volume_seasons().query("season == 2024"),
            games(
                [{"gsis_id": g, "week": w, "position": p, "targets": 12.0, "points": 6.0}
                 for g, p in (("wr1", "WR"), ("te1", "TE"), ("rb1", "RB")) for w in (1, 2, 3)]
            ),
        ]
    )  # fmt: skip
    tgts = pd.DataFrame(
        [{"gsis_id": g, "position": p, "team": "AAA", "opponent": "NOPE"}
         for g, p in (("rb1", "RB"), ("wr1", "WR"), ("te1", "TE"))]
    )  # fmt: skip
    ctx = Context(2025, 4)
    shipped = project_week(hist, tgts, ctx, None)
    mixed = project_week(hist, tgts, ctx, None, by_name("xfp_weight=0.5@WR"))
    assert mixed["gsis_id"].tolist() == ["rb1", "wr1", "te1"]
    assert mixed["points"].iloc[1] > shipped["points"].iloc[1]  # the receiver changed
    assert mixed["points"].iloc[0] == shipped["points"].iloc[0]  # nobody else did
    assert mixed["points"].iloc[2] == shipped["points"].iloc[2]
    empty = project_week(hist, tgts.iloc[0:0], ctx, None, by_name("xfp_weight=0.5@WR"))
    assert empty.empty


# --------------------------------------------------------------------------- sweep table
def test_sweep_table_ranks_ideas_and_applies_the_keep_rule() -> None:
    seasons = (2022, 2023, 2024)
    good = compare.summarize(
        "good",
        paired(flat(3.0), flat(0.0), seasons=seasons),
        paired(flat(3.0), flat(0.0), seasons=(2025,), seed=5),
    )
    bad = compare.summarize(
        "bad",
        paired(flat(0.0), flat(3.0), seasons=seasons),
        paired(flat(0.0), flat(3.0), seasons=(2025,), seed=5),
    )
    lopsided = {"QB": 3.0, "RB": 0.0, "WR": 0.0, "TE": 0.0}
    wr_only = compare.summarize(
        "partial",
        paired(flat(1.0), lopsided, seasons=seasons),
        paired(flat(1.0), lopsided, seasons=(2025,), seed=5),
    )
    assert good.verdict.kept and not bad.verdict.kept
    assert bad.worst_position[1] > 2.0
    assert wr_only.worst_position[0] == "QB" and wr_only.verdict.positions_kept
    text = compare.render_sweep("shipped", [bad, wr_only, good], "Sweep")
    lines = [line for line in text.splitlines() if line.startswith("| `")]
    assert [line.split("`")[1] for line in lines] == ["good", "partial", "bad"]  # best first
    assert "**kept**" in lines[0] and lines[2].endswith("| no |")
    assert "| for " in lines[1]


# --------------------------------------------------------------------------- data plumbing
def test_raw_stat_columns_ride_along_only_when_asked_for() -> None:
    rows = pd.DataFrame(
        [{"gsis_id": "a", "season": 2025, "week": 1, "position": "WR", "team": "AAA",
          "opponent": "KC", "snap": 0.9, "receiving_yards": 80.0, "targets": None}]
    )  # fmt: skip
    rules = {"rec_yd": 0.1}
    assert "targets" not in scored_history(rows, rules).columns  # the live frame is unchanged
    kept = scored_history(rows, rules, keep=("targets", "carries"))
    assert kept["points"].iloc[0] == pytest.approx(8.0)
    assert kept["targets"].iloc[0] == 0.0 and kept["carries"].iloc[0] == 0.0


def test_game_context_is_one_row_per_team_from_its_own_side(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = pl.DataFrame(
        [
            {"season": 2025, "game_type": "REG", "week": 1, "home_team": "LAR", "away_team": "KC",
             "spread_line": 3.0, "total_line": 47.0, "roof": "dome", "temp": None, "wind": None,
             "home_rest": 7, "away_rest": 10, "home_score": 27, "away_score": 20},
            {"season": 2025, "game_type": "POST", "week": 19, "home_team": "KC", "away_team": "LAR",
             "spread_line": 1.0, "total_line": 40.0, "roof": "outdoors", "temp": 30.0, "wind": 9.0,
             "home_rest": 7, "away_rest": 7, "home_score": 3, "away_score": 6},
        ]
    )  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_schedules", lambda seasons: raw)
    out = nflverse.load_game_context([2025]).sort("team")
    assert out["team"].to_list() == ["KC", "LA"]  # regular season only, canonical names
    kc, la = out.row(0, named=True), out.row(1, named=True)
    assert (la["home"], la["spread"], la["implied"], la["rest"]) == (True, 3.0, 25.0, 7)
    assert (kc["home"], kc["spread"], kc["implied"], kc["rest"]) == (False, -3.0, 22.0, 10)
    assert (kc["points_for"], kc["points_against"], kc["total"]) == (20.0, 27.0, 47.0)
    with pytest.raises(nflverse.NflverseSchemaError, match="spread_line"):
        monkeypatch.setattr(nflreadpy, "load_schedules", lambda seasons: raw.drop("spread_line"))
        nflverse.load_game_context([2025])


def test_draft_capital_keeps_players_with_an_id(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = pl.DataFrame(
        [
            {"season": 2025, "round": 1, "pick": 4, "gsis_id": "00-1", "position": "WR"},
            {"season": 2025, "round": 6, "pick": 190, "gsis_id": None, "position": "G"},
        ]
    )
    monkeypatch.setattr(nflreadpy, "load_draft_picks", lambda seasons: raw)
    out = nflverse.load_draft_capital([2025])
    assert out.to_dicts() == [{"gsis_id": "00-1", "draft_year": 2025, "round": 1, "pick": 4}]
