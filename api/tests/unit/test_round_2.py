"""P4 round 2 (ADR-058): the per-position tuner's search, and the ideas added for round 2
(nflverse expected points, depth-chart tier, teammate out, first game back)."""

import pickle
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any

import nflreadpy
import numpy as np
import pandas as pd
import polars as pl
import pytest

from app.model.config import SHIPPED, ModelConfig
from app.model.features.context import availability, build_extras
from app.scripts import backtest, tune
from app.sources import nflverse
from tests.unit.test_compare import frame
from tests.unit.test_model_ideas import factor, games, has, one, schedule, target

# --------------------------------------------------------------------------- tuner search
BEST_XFP, BEST_HALF_LIFE = 0.6, 9.0


def fake_runner(calls: list[ModelConfig] | None = None) -> tune.Runner:
    """Receivers whose projection misses by |xfp_weight - 0.6| * 4 + |half_life - 9| * 0.1,
    plus a fixed bit of noise, so the best settings are known in advance."""
    base = frame(dict.fromkeys(("QB", "RB", "WR", "TE"), 0.0), seasons=(2022, 2023, 2024))
    base = base[base["position"] == "WR"].reset_index(drop=True)
    noise = np.random.default_rng(7).normal(0, 1.0, len(base))

    def run(configs: Any) -> list[pd.DataFrame]:
        out = []
        for cfg in configs:
            if calls is not None:
                calls.append(cfg)
            off = abs(cfg.xfp_weight - BEST_XFP) * 4 + abs(cfg.half_life - BEST_HALF_LIFE) * 0.1
            out.append(base.assign(proj=base["actual"] + noise + off))
        return out

    return run


GRID = {"half_life": [2.0, 4.0, 9.0, 14.0], "xfp_weight": [0.0, 0.25, 0.5, 0.75, 1.0]}


def test_sweep_tries_every_value_alone_and_orders_settings_by_their_best_gain() -> None:
    calls: list[ModelConfig] = []
    result = tune.sweep(fake_runner(calls), "WR", GRID)
    assert len(result["rows"]) == 3 + 4  # shipped values (half_life 4, xfp 0) are not repeated
    assert all(
        c == SHIPPED or sum(getattr(c, n) != getattr(SHIPPED, n) for n in GRID) == 1 for c in calls
    )  # every trial changes one setting only
    assert result["order"] == ["xfp_weight", "half_life"]  # 2.4 points to gain against 0.5
    best = min(result["rows"], key=lambda r: r["all"]["change"])
    assert (best["setting"], best["value"]) == ("xfp_weight", 0.5)
    assert best["all"]["result"] == "better" and {"5+", "1-4"} <= set(best)


def test_descend_then_refine_finds_the_best_settings_between_grid_points() -> None:
    run = fake_runner()
    tuned, tuned_miss, steps = tune.descend(run, "WR", GRID, ["xfp_weight", "half_life"])
    assert (tuned.xfp_weight, tuned.half_life) == (0.5, 9.0)
    assert [s["setting"] for s in steps[1:]] == ["xfp_weight", "half_life"]
    refined, refined_miss, more = tune.refine(run, "WR", GRID, tuned, tuned_miss)
    assert refined.xfp_weight == 0.625  # halfway between 0.5 and 0.75, closer to 0.6
    assert refined.half_life == 9.0  # 6.5 and 11.5 are both further from 9
    assert refined_miss < tuned_miss and more[0]["step"] == "refine 1"
    assert tune.changed(refined, GRID) == {"xfp_weight": 0.625, "half_life": 9.0}


def test_a_gain_inside_the_noise_threshold_is_not_taken() -> None:
    tiny = {"half_life": [4.0, 4.01]}

    def run(configs: Any) -> list[pd.DataFrame]:
        return [fake_runner()([replace(c, half_life=4.0)])[0] for c in configs]

    tuned, _, steps = tune.descend(run, "WR", tiny, ["half_life"])
    assert tuned == SHIPPED and len(steps) == 1


def test_only_plain_numbers_are_refined() -> None:
    assert tune.between("xfp_weight", 0.5, [0.0, 0.25, 0.5, 0.75]) == [0.375, 0.625]
    assert tune.between("xfp_weight", 1.0, [0.0, 0.5, 1.0]) == [0.75]  # nothing above the top
    assert tune.between("role_window", 2, [1, 2, 3]) == []  # whole numbers: no new value between
    assert tune.between("role_window", 1, [1, 3]) == [2]
    assert tune.between("def_pass", True, [False, True]) == []
    assert tune.between("prior_games_opener", None, [None, 1.5, 3.0]) == []
    assert tune.between("opp_fade_games", tune.OFF, [8.0, 16.0, tune.OFF]) == []
    assert tune.between("opp_fade_games", 16.0, [8.0, 16.0, tune.OFF]) == [12.0]


def test_check_judges_all_weeks_on_both_sets_of_seasons() -> None:
    seasons = (2022, 2023, 2024, 2025)
    base = frame(dict.fromkeys(("QB", "RB", "WR", "TE"), 2.0), seasons=seasons)
    base = base[base["position"] == "WR"].reset_index(drop=True)

    def run_all(configs: Any) -> list[pd.DataFrame]:
        return [base if c == SHIPPED else base.assign(proj=base["actual"]) for c in configs]

    result = tune.check(run_all, "WR", replace(SHIPPED, xfp_weight=0.5))
    assert result["kept"]
    assert result["tuning"]["all"]["result"] == result["check"]["all"]["result"] == "better"
    assert result["check"]["all"]["n"] < result["tuning"]["all"]["n"]  # one season against three


def test_settings_round_trip_through_the_saved_results() -> None:
    settings = {"xfp_weight": 0.625, "def_pass": True}
    assert tune.spec("WR", settings) == "xfp_weight=0.625@WR+def_pass=True@WR"
    cfg = tune.from_settings(settings)
    assert (cfg.xfp_weight, cfg.def_pass) == (0.625, True)
    with pytest.raises(SystemExit, match="nope"):
        tune.from_settings({"nope": 1})


def test_a_re_run_keeps_earlier_looks_at_the_check_season_on_record() -> None:
    results: dict[str, Any] = {"check": {"kept": False}}
    tune.retire_check(results)
    assert "check" not in results and results["earlier_checks"] == [{"kept": False}]
    tune.retire_check(results)  # nothing to retire
    assert len(results["earlier_checks"]) == 1


def test_the_vault_page_shows_each_stage_and_the_verdict() -> None:
    run = fake_runner()
    results: dict[str, Any] = {"date": "2026-11-13", "sweep": tune.sweep(run, "WR", GRID)}
    page = tune.render("WR", results)
    assert page.startswith("---\ntitle:") and "## Sweep" in page and "## Tune" not in page
    tuned, _tuned_miss, steps = tune.descend(run, "WR", GRID, results["sweep"]["order"])
    results["tune"] = {"settings": tune.changed(tuned, GRID), "steps": steps}
    cell = {"change": -0.1, "low": -0.2, "high": -0.05, "result": "better"}
    part = {"all": cell, "5+": cell, "1-4": cell}
    results["check"] = {"tuning": part, "check": part, "kept": True}
    results["earlier_checks"] = [{"kept": False}]
    page = tune.render("WR", results)
    assert "## Tune" in page and "`xfp_weight` 0.5" in page and "Verdict: **kept**" in page
    assert "opened 2 times" in page
    assert page.rstrip().splitlines()[-1].startswith("Related:")
    assert "every game" in tune.render("K", {"date": "x"})  # K and DEF are not a startable slice


def tiny_history() -> pd.DataFrame:
    rows = [
        {"gsis_id": f"w{i}", "season": s, "week": w, "position": "WR", "team": "AAA",
         "opponent": "BBB", "points": float(5 + i + w % 3), "snap": 0.8, "injury_game": None}
        for s in (2021, 2022) for w in range(1, 7) for i in range(4)
    ]  # fmt: skip
    return pd.DataFrame(rows)


def test_parallel_runs_give_the_same_answer_as_one_process(tmp_path: Path) -> None:
    data = tmp_path / "data.pkl"
    data.write_bytes(pickle.dumps({"history": tiny_history(), "extras": None}))
    tune._init_worker(str(data))
    configs = [SHIPPED, replace(SHIPPED, half_life=9.0)]
    inline = tune.make_runner(None, "WR", [2022])(configs)
    with ProcessPoolExecutor(2, initializer=tune._init_worker, initargs=(str(data),)) as pool:
        parallel = tune.make_runner(pool, "WR", [2022])(configs)
    for a, b in zip(inline, parallel, strict=True):
        pd.testing.assert_frame_equal(a, b)
    assert not inline[0]["proj"].equals(inline[1]["proj"])


# --------------------------------------------------------------------------- E-04 nflverse volume
def test_nflverse_expected_points_pull_a_player_toward_his_volume() -> None:
    hist = games(
        [{"gsis_id": "wr1", "week": w, "points": 6.0, "xfp_nflverse": 14.0} for w in (1, 2, 3)]
    )
    tgt = target(opp="NOPE")
    shipped = one(hist, tgt, SHIPPED, week=4)["points"]
    half = one(hist, tgt, ModelConfig(nfl_xfp_weight=0.5), week=4)
    # own points blend to 6; nflverse volume: 3 games at 14 + the position floor 6 (3 games) = 10
    assert (shipped, half["points"]) == (6.0, 8.0)
    assert "50% from nflverse expected points" in factor(half, "baseline")["note"]
    # a game nflverse has no row for, or no column at all, counts at face value
    missing = hist.assign(xfp_nflverse=np.nan)
    assert one(missing, tgt, ModelConfig(nfl_xfp_weight=0.5), week=4)["points"] == shipped
    bare = hist.drop(columns=["xfp_nflverse"])
    assert one(bare, tgt, ModelConfig(nfl_xfp_weight=0.5), week=4)["points"] == shipped


# --------------------------------------------------------------------------- E-14 depth tier
def depth_history() -> pd.DataFrame:
    """2024: starters average 9, next-in-line receivers 6. 2025: wr1 is next in line."""
    rows = [{"gsis_id": f"s{i}", "season": 2024, "week": w, "points": 9.0, "depth_tier": 1}
            for i in range(3) for w in (1, 2)]  # fmt: skip
    rows += [{"gsis_id": f"b{i}", "season": 2024, "week": w, "points": 6.0, "depth_tier": 2}
             for i in range(3) for w in (1, 2)]  # fmt: skip
    rows += [{"gsis_id": "wr1", "week": w, "points": 6.0, "depth_tier": 2} for w in (1, 2, 3)]
    return games(rows)


def depth_target(tier: Any) -> pd.DataFrame:
    return target(opp="NOPE").assign(depth_tier=tier)


def test_a_promotion_on_the_depth_chart_raises_the_projection() -> None:
    hist = depth_history()
    cfg = ModelConfig(depth_rank=0.5)
    up = one(hist, depth_target(1), cfg, week=4)
    step = factor(up, "depth chart")
    assert step["value"] == pytest.approx(1 + 0.5 * (9 / 6 - 1))
    assert step["note"] == "Starter this week, usually next in line"
    assert not has(one(hist, depth_target(2), cfg, week=4), "depth chart")  # no change
    assert not has(one(hist, depth_target(None), cfg, week=4), "depth chart")  # no chart
    assert not has(one(hist, depth_target(1), SHIPPED, week=4), "depth chart")
    big = factor(one(hist, depth_target(1), ModelConfig(depth_rank=5.0), week=4), "depth chart")
    assert big["value"] == 1.5  # limited


def test_the_depth_table_never_reads_the_season_being_projected() -> None:
    hist = depth_history()
    later = games([{"gsis_id": f"x{i}", "week": 1, "points": 90.0, "depth_tier": 1}
                   for i in range(5)])  # fmt: skip
    cfg = ModelConfig(depth_rank=0.5)
    a = factor(one(hist, depth_target(1), cfg, week=4), "depth chart")
    b = factor(one(pd.concat([hist, later]), depth_target(1), cfg, week=4), "depth chart")
    assert a == b


def test_a_player_with_no_games_this_season_uses_last_seasons_tier() -> None:
    hist = depth_history()
    hist = hist[~(hist["gsis_id"] == "wr1")]
    last = games([{"gsis_id": "wr1", "season": 2024, "week": w, "points": 6.0, "depth_tier": 2}
                  for w in (3, 4)])  # fmt: skip
    row = one(pd.concat([hist, last]), depth_target(1), ModelConfig(depth_rank=0.5), week=1)
    assert has(row, "depth chart")


# --------------------------------------------------------------------------- E-15, E-20
def injuries(rows: list[tuple[str, int, int, str | None, str | None]]) -> pd.DataFrame:
    return pd.DataFrame(
        rows, columns=["gsis_id", "season", "week", "report_status", "roster_status"]
    )


def test_availability_reads_the_game_report_and_reserve_lists() -> None:
    out, reserve = availability(
        injuries(
            [
                ("a", 2025, 4, "Out", None),
                ("b", 2025, 4, "Doubtful", None),
                ("c", 2025, 4, "Questionable", None),
                ("d", 2025, 4, None, "RES"),
            ]
        )
    )
    assert out == {("a", 2025, 4), ("b", 2025, 4), ("d", 2025, 4)}
    assert reserve == {("d", 2025, 4)}
    assert availability(injuries([])) == (set(), set())


def room(star_last_week: int = 3) -> pd.DataFrame:
    rows = [
        {"gsis_id": "star", "week": w, "points": 20.0} for w in (1, 2, 3) if w <= star_last_week
    ]
    rows += [{"gsis_id": "wr1", "week": w, "points": 10.0} for w in (1, 2, 3)]
    rows += [{"gsis_id": "scrub", "week": w, "points": 2.0} for w in (1, 2, 3)]
    return games(rows)


def test_a_player_moves_up_when_a_better_teammate_is_newly_out() -> None:
    cfg = ModelConfig(teammate_out=0.1)
    extras = build_extras(schedule(), injuries=injuries([("star", 2025, 4, "Out", None)]))
    row = one(room(), target(), cfg, extras, week=4)
    assert factor(row, "teammate out")["value"] == pytest.approx(1.1)
    assert not has(one(room(), target(), SHIPPED, extras, week=4), "teammate out")
    assert not has(one(room(), target(), cfg, None, week=4), "teammate out")
    # long gone (last played week 1): his absence is already in wr1's own recent games
    gone = build_extras(schedule(), injuries=injuries([("star", 2025, 5, "Out", None)]))
    assert not has(one(room(star_last_week=1), target(), cfg, gone, week=5), "teammate out")
    # a worse teammate out does not matter
    scrub = build_extras(schedule(), injuries=injuries([("scrub", 2025, 4, "Out", None)]))
    assert not has(one(room(), target(), cfg, scrub, week=4), "teammate out")


def test_the_first_game_back_from_a_reserve_list_is_discounted() -> None:
    cfg = ModelConfig(return_discount=0.1)
    hist = games([{"gsis_id": "wr1", "week": w, "points": 10.0} for w in (1, 2)])
    stay = injuries([("wr1", 2025, 3, None, "RES"), ("wr1", 2025, 4, None, "RES")])
    extras = build_extras(schedule(), injuries=stay)
    step = factor(one(hist, target(), cfg, extras, week=5), "first game back")
    assert step["value"] == 0.9 and step["note"] == "Back from a reserve list (weeks 3-4)"
    assert not has(one(hist, target(), cfg, build_extras(schedule()), week=5), "first game back")
    # once he has played again, the next game is normal
    again = pd.concat([hist, games([{"gsis_id": "wr1", "week": 5, "points": 10.0}])])
    assert not has(one(again, target(), cfg, extras, week=6), "first game back")


# --------------------------------------------------------------------------- data plumbing
def test_expected_stats_are_renamed_for_the_scoring_map(monkeypatch: pytest.MonkeyPatch) -> None:
    row: dict[str, Any] = dict.fromkeys(nflverse.EXPECTED_STAT_COLUMNS, 0.0)
    row |= {"season": "2025", "week": 3.0, "player_id": "00-1", "receptions_exp": 4.5}
    row |= {"rec_yards_gained_exp": 52.0, "rec_attempt": 7.0, "rec_touchdown_exp": None}
    raw = pl.DataFrame([row, {**row, "player_id": None}])
    monkeypatch.setattr(nflreadpy, "load_ff_opportunity", lambda seasons: raw)
    out = nflverse.load_expected_stats([2025]).row(0, named=True)
    assert (out["gsis_id"], out["season"], out["week"]) == ("00-1", 2025, 3)
    assert (out["receptions"], out["receiving_yards"], out["targets"]) == (4.5, 52.0, 7.0)
    assert out["receiving_tds"] == 0.0
    with pytest.raises(nflverse.NflverseSchemaError, match="receptions_exp"):
        monkeypatch.setattr(nflreadpy, "load_ff_opportunity", lambda s: raw.drop("receptions_exp"))
        nflverse.load_expected_stats([2025])


def test_depth_tiers_from_both_chart_formats(monkeypatch: pytest.MonkeyPatch) -> None:
    weekly = pl.DataFrame(
        [
            {"season": 2024, "week": 1, "game_type": "REG", "gsis_id": "a", "depth_team": "1",
             "depth_position": "WR", "formation": "Offense"},
            {"season": 2024, "week": 1, "game_type": "REG", "gsis_id": "a", "depth_team": "2",
             "depth_position": "WR", "formation": "Offense"},
            {"season": 2024, "week": 1, "game_type": "REG", "gsis_id": "b", "depth_team": "4",
             "depth_position": "RB", "formation": "Offense"},
            {"season": 2024, "week": 1, "game_type": "REG", "gsis_id": "c", "depth_team": "1",
             "depth_position": "KR", "formation": "Special Teams"},
        ]
    )  # fmt: skip
    snaps = pl.DataFrame(
        [
            {"dt": "2025-09-06T07:00:00Z", "gsis_id": "w4", "pos_abb": "WR", "pos_rank": 4},
            {"dt": "2025-09-06T07:00:00Z", "gsis_id": "w6", "pos_abb": "WR", "pos_rank": 6},
            {"dt": "2025-09-06T07:00:00Z", "gsis_id": "r2", "pos_abb": "RB", "pos_rank": 2},
            # game day of week 1: too late for week 1, used for week 2
            {"dt": "2025-09-07T07:00:00Z", "gsis_id": "w4", "pos_abb": "WR", "pos_rank": 2},
            {"dt": "2025-09-07T07:00:00Z", "gsis_id": "lb", "pos_abb": "MLB", "pos_rank": 1},
        ]
    )  # fmt: skip
    games_2025 = pl.DataFrame(
        [{"season": 2025, "week": 1, "game_type": "REG", "gameday": "2025-09-07"},
         {"season": 2025, "week": 2, "game_type": "REG", "gameday": "2025-09-14"},
         {"season": 2025, "week": 1, "game_type": "PRE", "gameday": "2025-08-01"}]
    )  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_depth_charts", lambda s: weekly if s == [2024] else snaps)
    monkeypatch.setattr(nflreadpy, "load_schedules", lambda s: games_2025)
    out = nflverse.load_depth_tiers([2024, 2025]).sort(["season", "week", "gsis_id"])
    got = {
        (r["season"], r["week"], r["gsis_id"]): r["depth_tier"] for r in out.iter_rows(named=True)
    }
    assert got == {
        (2024, 1, "a"): 1, (2024, 1, "b"): 3,  # best level that week; capped at 3
        (2025, 1, "r2"): 2, (2025, 1, "w4"): 2, (2025, 1, "w6"): 3,  # WR4-5 next in line
        (2025, 2, "w4"): 1,  # the game-day snapshot counts from the next week on
    }  # fmt: skip
    assert nflverse.load_depth_tiers([]).columns == ["gsis_id", "season", "week", "depth_tier"]


def test_round_2_columns_join_onto_history(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = pl.DataFrame(
        [{"gsis_id": "a", "season": 2025, "week": 1, **dict.fromkeys(
            nflverse.EXPECTED_STAT_COLUMNS.values(), 0.0), "receiving_yards": 50.0,
          "receptions": 4.0}]
    )  # fmt: skip
    depth = pl.DataFrame([{"gsis_id": "a", "season": 2025, "week": 1, "depth_tier": 1}])
    monkeypatch.setattr(nflverse, "load_expected_stats", lambda s: expected)
    monkeypatch.setattr(nflverse, "load_depth_tiers", lambda s: depth)
    history = games([{"gsis_id": "a", "week": 1}, {"gsis_id": "b", "week": 1}])
    out = backtest.with_round_2_columns(history, [2025], backtest.SCORING["full"])
    assert out.loc[out["gsis_id"] == "a", "xfp_nflverse"].iloc[0] == pytest.approx(9.0)
    assert out.loc[out["gsis_id"] == "a", "depth_tier"].iloc[0] == 1
    assert out.loc[out["gsis_id"] == "b", ["xfp_nflverse", "depth_tier"]].isna().all(axis=None)
    assert len(out) == len(history)


def test_the_depth_tier_reaches_the_projection_only_when_the_idea_is_on() -> None:
    hist = depth_history()
    hist.loc[(hist["gsis_id"] == "wr1") & (hist["week"] == 3), "depth_tier"] = 1
    hist["opponent"] = "Z"
    hist["injury_game"] = None
    shipped = backtest.walk_forward(hist, [2025], SHIPPED, positions=("WR",))
    plain = backtest.walk_forward(hist.drop(columns=["depth_tier"]), [2025], positions=("WR",))
    assert shipped["proj"].tolist() == plain["proj"].tolist()
    on = backtest.walk_forward(hist, [2025], ModelConfig(depth_rank=0.5), positions=("WR",))
    week3 = on[(on["gsis_id"] == "wr1") & (on["week"] == 3)]["proj"].iloc[0]
    assert week3 > shipped[(shipped["gsis_id"] == "wr1") & (shipped["week"] == 3)]["proj"].iloc[0]


def test_a_later_sweep_of_new_settings_joins_the_earlier_one() -> None:
    run = fake_runner()
    first = tune.merge_sweep(None, tune.sweep(run, "WR", {"half_life": GRID["half_life"]}), GRID)
    assert first["order"] == ["half_life"]
    both = tune.merge_sweep(first, tune.sweep(run, "WR", {"xfp_weight": GRID["xfp_weight"]}), GRID)
    assert both["order"] == ["xfp_weight", "half_life"] and len(both["rows"]) == 3 + 4
    again = tune.merge_sweep(both, tune.sweep(run, "WR", {"half_life": [2.0]}), GRID)
    assert len(again["rows"]) == 1 + 4  # a re-swept setting replaces its old rows
    with pytest.raises(SystemExit, match="re-run it whole"):
        tune.merge_sweep({**both, "shipped_miss": 99.0}, first, GRID)


# --------------------------------------------------------------------------- RB ideas (E-34..36)
def back(rows: list[tuple[int, float, float, float, float]], season: int = 2025) -> pd.DataFrame:
    """rows: (week, carries, rushing_yards, receptions, receiving_yards) for rb1; points are the
    full-PPR sum of those."""
    return games(
        [
            {"gsis_id": "rb1", "season": season, "week": w, "position": "RB", "carries": c,
             "rushing_yards": ry, "receptions": rec, "receiving_yards": recy,
             "points": 0.1 * ry + rec + 0.1 * recy}
            for w, c, ry, rec, recy in rows
        ]
    )  # fmt: skip


def rb_target(team: str = "AAA") -> pd.DataFrame:
    return target("rb1", "RB", "NOPE", team)


def test_split_rushing_and_receiving_equals_the_shipped_baseline_with_one_memory() -> None:
    hist = pd.concat(
        [back([(w, 15, 60, 2, 15) for w in range(1, 17)], 2024),
         back([(1, 20, 120, 1, 5), (2, 10, 30, 6, 60), (3, 18, 90, 3, 20)])]
    )  # fmt: skip
    shipped = one(hist, rb_target(), SHIPPED, week=4)
    same = one(hist, rb_target(), ModelConfig(receiving_half_life=4.0), week=4)
    assert same["points"] == pytest.approx(shipped["points"])
    assert "averaged apart" in factor(same, "baseline")["note"]
    longer = one(hist, rb_target(), ModelConfig(receiving_half_life=14.0), week=4)
    assert longer["points"] != pytest.approx(shipped["points"])


def test_receiving_share_and_yards_per_carry_luck() -> None:
    from app.model.features import rushing

    df = back([(1, 10, 100, 2, 20), (2, 0, 0, 0, 0)])
    share = rushing.receiving_share(df)
    assert share.iloc[0] == pytest.approx((1 + 2) / (1 + 2 + 10))  # half-PPR reference weights
    assert np.isnan(share.iloc[1])
    league = back([(w, 20, 80, 0, 0) for w in range(1, 30)], 2024)  # 4.0 a carry
    ypc = rushing.fit_ypc(pd.concat([league, df]), 2025)
    assert ypc == {"RB": pytest.approx(4.0)}
    assert rushing.fit_ypc(df, 2025) == {}  # too few earlier carries to fit
    # 10 carries for 100 yards: 60 yards above the norm, 6 points; half of it removed
    assert rushing.regress_ypc(df, ypc, 0.5).iloc[0] == pytest.approx(df["points"].iloc[0] - 3)


def test_yards_per_carry_luck_lowers_a_back_running_hot() -> None:
    league = back([(w, 20, 80, 0, 0) for w in range(1, 30)], 2024).assign(gsis_id="lg")
    hot = back([(w, 12, 90, 1, 5) for w in (1, 2, 3)])
    hist = pd.concat([league, hot])
    shipped = one(hist, rb_target(), SHIPPED, week=4)["points"]
    assert one(hist, rb_target(), ModelConfig(ypc_regression=0.5), week=4)["points"] < shipped


def test_carry_volume_follows_his_share_and_the_teams_expected_carries() -> None:
    from app.model.features import rushing

    rows = [(w, c, 4 * c, 1, 5) for w, c in ((1, 10), (2, 10), (3, 18), (4, 18))]
    hist = back(rows)
    other = games(
        [{"gsis_id": "rb2", "week": w, "position": "RB", "carries": 20 - c}
         for w, c in ((1, 10), (2, 10), (3, 18), (4, 18))]
    )  # fmt: skip
    hist = pd.concat([hist, other])
    cfg = ModelConfig(carry_volume=1.0)
    row = one(hist, rb_target(), cfg, week=5)
    step = factor(row, "carry volume")
    assert step["value"] > 1.0 and "Share of team carries last 2 games 90%" in step["note"]
    assert not has(one(hist, rb_target(), SHIPPED, week=5), "carry volume")
    # the betting line adds the team's expected carries when a fit and a game exist
    past = []
    for s in (2023, 2024):
        for w in range(1, 18):
            for team, carries in (("AAA", 30.0), ("KC", 20.0)):
                past.append({"gsis_id": f"{team}{s}", "season": s, "week": w,
                             "position": "RB", "team": team, "carries": carries})  # fmt: skip
    lines = {(t, s, w): {"spread": 5.0 if t == "AAA" else -5.0}
             for s in (2023, 2024) for w in range(1, 18) for t in ("AAA", "KC")}  # fmt: skip
    fit = rushing.fit_carries_vs_spread(games(past), lines, 2025)
    assert fit is not None and fit.per_point == pytest.approx(1.0)
    assert fit.intercept == pytest.approx(25.0)
    assert rushing.fit_carries_vs_spread(games(past), {}, 2025) is None
    assert rushing.fit_carries_vs_spread(games(past), lines, 2023) is None
    extras = build_extras(schedule())
    extras.cache[("carries", 2025)] = fit
    favoured = factor(one(hist, rb_target(), cfg, extras, week=4), "carry volume")
    assert "expected" in favoured["note"]


def test_no_round_2_idea_reads_the_week_being_projected_or_later() -> None:
    cfg = ModelConfig(
        nfl_xfp_weight=0.5, depth_rank=0.5, teammate_out=0.1, return_discount=0.1,
        receiving_half_life=9.0, ypc_regression=0.5, carry_volume=0.5,
    )  # fmt: skip
    league = back([(w, 20, 80, 0, 0) for w in range(1, 30)], 2024).assign(gsis_id="lg")
    past = pd.concat(
        [league, depth_history(), back([(w, 12, 50, 2, 15) for w in (1, 2, 3)]), room()]
    ).assign(xfp_nflverse=9.0)
    future = back([(w, 30, 300, 9, 150) for w in (4, 5, 6)]).assign(xfp_nflverse=40.0, depth_tier=1)
    extras = build_extras(schedule(), injuries=injuries([("star", 2025, 4, "Out", None)]))
    for tgt in (rb_target(), depth_target(1), target()):
        a = one(past, tgt, cfg, extras, week=4)
        b = one(pd.concat([past, future]), tgt, cfg, extras, week=4)
        assert a["points"] == b["points"] and a["factors"] == b["factors"]
