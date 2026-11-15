"""P4 step 3 training data (ADR-062, ADR-063): depth-chart tiers in both nflverse formats, and
player background. The depth tests include the leak rule: a week never reads a chart published
on or after its first game day."""

from datetime import date
from typing import Any

import nflreadpy
import polars as pl
import pytest

from app.sources import nflverse
from app.sources.nflverse import NflverseSchemaError
from tests import nflverse_fakes as fake


def tiers(df: pl.DataFrame) -> dict[tuple[str, int, int], int]:
    rows = df.select("gsis_id", "season", "week", "depth_tier").rows()
    return {(g, s, w): t for g, s, w, t in rows}


# --------------------------------------------------------------------------- up to 2024
def test_weekly_charts_take_the_best_level_and_cap_it_at_three(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows: list[dict[str, Any]] = [
        # a receiver listed in two formation slots, starter in one: tier 1
        {"season": 2023, "week": 11, "gsis_id": "wr", "depth_team": "2", "depth_position": "WR"},
        {"season": 2023, "week": 11, "gsis_id": "wr", "depth_team": "1", "depth_position": "WR"},
        # fourth on the chart: deeper (3)
        {"season": 2023, "week": 11, "gsis_id": "rb", "depth_team": "4", "depth_position": "RB"},
        # left out: defense, kicker, no id, postseason
        {"season": 2023, "week": 11, "gsis_id": "lb", "depth_team": "1", "depth_position": "LB",
         "formation": "Defense"},
        {"season": 2023, "week": 11, "gsis_id": "k", "depth_team": "1", "depth_position": "K"},
        {"season": 2023, "week": 11, "gsis_id": None, "depth_team": "1", "depth_position": "QB"},
        {"season": 2023, "week": 19, "gsis_id": "wr", "depth_team": "1", "depth_position": "WR",
         "game_type": "WC"},
    ]  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_depth_charts", lambda s: fake.depth_charts_weekly(rows))
    assert tiers(nflverse.load_depth_tiers([2023])) == {("wr", 2023, 11): 1, ("rb", 2023, 11): 3}


# --------------------------------------------------------------------------- 2025 on
SCHEDULE_2025 = pl.DataFrame(
    {
        "season": [2025, 2025, 2025],
        "week": [1, 1, 2],
        "game_type": ["REG", "REG", "REG"],
        "gameday": ["2025-09-04", "2025-09-07", "2025-09-11"],  # week 1 opens on a Thursday
    }
)


def snapshots(rows: list[tuple[str, str, str, int]]) -> pl.DataFrame:
    return fake.depth_charts_snapshots(
        [{"dt": dt, "gsis_id": g, "pos_abb": pos, "pos_rank": r} for dt, g, pos, r in rows]
    )


def test_snapshots_use_the_last_chart_before_the_first_game_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    charts = snapshots(
        [
            ("2025-09-01T12:00:00Z", "wr", "WR", 4),  # Monday of week 1: WR4, next in line
            ("2025-09-04T12:00:00Z", "wr", "WR", 1),  # week 1's first game day: too late
            ("2025-09-08T12:00:00Z", "wr", "WR", 1),  # before week 2: starter
        ]
    )
    monkeypatch.setattr(nflreadpy, "load_schedules", lambda s: SCHEDULE_2025)
    monkeypatch.setattr(nflreadpy, "load_depth_charts", lambda s: charts)
    assert tiers(nflverse.load_depth_tiers([2025])) == {("wr", 2025, 1): 2, ("wr", 2025, 2): 1}


def test_snapshot_tiers_by_position(monkeypatch: pytest.MonkeyPatch) -> None:
    """Receivers 1-3 start and 4-5 are next in line; other positions go 1, 2, then deeper."""
    day = "2025-09-01T12:00:00Z"
    charts = snapshots(
        [
            (day, "wr3", "WR", 3), (day, "wr5", "WR", 5), (day, "wr6", "WR", 6),
            (day, "rb2", "RB", 2), (day, "te5", "TE", 5), (day, "qb1", "QB", 1),
            (day, "k1", "K", 1),  # not an offensive skill position: left out
        ]
    )  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_schedules", lambda s: SCHEDULE_2025.head(1))
    monkeypatch.setattr(nflreadpy, "load_depth_charts", lambda s: charts)
    got = {g: t for (g, _, _), t in tiers(nflverse.load_depth_tiers([2025])).items()}
    assert got == {"wr3": 1, "wr5": 2, "wr6": 3, "rb2": 2, "te5": 3, "qb1": 1}


def test_a_week_with_no_earlier_chart_has_no_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    charts = snapshots([("2025-09-09T12:00:00Z", "wr", "WR", 1)])  # only after week 1 began
    monkeypatch.setattr(nflreadpy, "load_schedules", lambda s: SCHEDULE_2025)
    monkeypatch.setattr(nflreadpy, "load_depth_charts", lambda s: charts)
    assert tiers(nflverse.load_depth_tiers([2025])) == {("wr", 2025, 2): 1}


def test_both_formats_in_one_load(monkeypatch: pytest.MonkeyPatch) -> None:
    weekly = fake.depth_charts_weekly(
        [{"season": 2024, "week": 1, "gsis_id": "wr", "depth_team": "1", "depth_position": "WR"}]
    )
    dated = snapshots([("2025-09-01T12:00:00Z", "wr", "WR", 2)])
    monkeypatch.setattr(nflreadpy, "load_schedules", lambda s: SCHEDULE_2025.head(1))
    monkeypatch.setattr(nflreadpy, "load_depth_charts", lambda s: weekly if s == [2024] else dated)
    assert tiers(nflverse.load_depth_tiers([2024, 2025])) == {
        ("wr", 2024, 1): 1,
        ("wr", 2025, 1): 1,
    }


# --------------------------------------------------------------------------- background
def test_player_background(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = fake.players(
        [
            {"gsis_id": "00-0039075", "birth_date": "2001-05-29", "rookie_season": 2023,
             "draft_year": 2023, "draft_round": 5, "draft_pick": 177},
            {"gsis_id": "00-0033699", "birth_date": "1995-05-17", "rookie_season": 2017},
            {"gsis_id": None, "birth_date": "1990-01-01"},  # no NFL id: dropped
            {"gsis_id": "00-0039075", "birth_date": "2001-05-29"},  # a repeat: kept once
        ]
    )  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_players", lambda: raw)
    out = {r["gsis_id"]: r for r in nflverse.load_player_background().to_dicts()}
    assert set(out) == {"00-0039075", "00-0033699"}
    assert out["00-0039075"]["birth_date"] == date(2001, 5, 29)
    assert out["00-0039075"]["draft_round"] == 5 and out["00-0039075"]["draft_pick"] == 177
    assert out["00-0033699"]["draft_round"] is None  # undrafted


def test_player_background_needs_its_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        nflreadpy, "load_players", lambda: fake.players([{"gsis_id": "x"}]).drop("draft_pick")
    )
    with pytest.raises(NflverseSchemaError, match="draft_pick"):
        nflverse.load_player_background()


# --------------------------------------------------------------------------- injury formats
def test_injury_reports_from_2016_with_decimal_seasons(monkeypatch: pytest.MonkeyPatch) -> None:
    """Up to 2020 nflverse stores season and week as decimals; they must still join the rosters."""
    raw = fake.injuries(
        [
            {"gsis_id": "a", "season": 2016.0, "week": 3.0, "report_status": "Questionable",
             "date_modified": "2016-09-21T00:00:00Z"},
            {"gsis_id": "a", "season": 2016.0, "week": 3.0, "report_status": "Out",
             "date_modified": "2016-09-23T00:00:00Z"},
        ]
    )  # fmt: skip
    rosters = fake.rosters_weekly([{"gsis_id": "b", "season": 2016, "week": 3, "status": "RES"}])
    monkeypatch.setattr(nflreadpy, "load_injuries", lambda s: raw)
    monkeypatch.setattr(nflreadpy, "load_rosters_weekly", lambda s: rosters)
    out = {r["gsis_id"]: r for r in nflverse.load_injury_reports([2016]).to_dicts()}
    assert out["a"]["report_status"] == "Out" and out["a"]["season"] == 2016  # latest filed
    assert out["b"]["roster_status"] == "RES" and out["b"]["week"] == 3


def test_injury_reports_without_date_modified(monkeypatch: pytest.MonkeyPatch) -> None:
    """From 2025 the file is one row per player-week with no date_modified column; loading the
    current season alone (the daily refresh) must still work."""
    raw = fake.injuries(
        [{"gsis_id": "a", "season": 2026, "week": 10, "report_status": "Doubtful"}]
    ).drop("date_modified")
    monkeypatch.setattr(nflreadpy, "load_injuries", lambda s: raw)
    active = fake.rosters_weekly([{"gsis_id": "z", "season": 2026, "week": 10}])
    monkeypatch.setattr(nflreadpy, "load_rosters_weekly", lambda s: active)
    out = nflverse.load_injury_reports([2026]).to_dicts()
    assert [(r["gsis_id"], r["report_status"]) for r in out] == [("a", "Doubtful")]
