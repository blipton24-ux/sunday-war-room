"""Edge cases the main suites didn't reach, found by a coverage run (step 14).

Each test pins behavior that matters: what happens at the boundary, not the happy path.
"""

import time
from typing import Any

import httpx
import jwt
import nflreadpy
import pandas as pd
import polars as pl
import pytest
import respx
from fastapi.testclient import TestClient

from app.adapters.base import AdapterError, AdapterSchemaError, NotFoundOnPlatform
from app.adapters.sleeper import BASE_URL, SleeperAdapter
from app.auth.tokens import InvalidToken, decode_api_token
from app.config import get_settings
from app.main import app
from app.model.distribution import (
    Calibration,
    PositionFit,
    apply_range,
    load_calibration,
)
from app.model.projection import Context, project_week
from app.model.winprob import SimPlayer, simulate
from app.services import ingest
from app.sources import nflverse
from tests import nflverse_fakes as fake


# --------------------------------------------------------------------------- tokens and errors
def test_token_with_a_non_numeric_subject_is_rejected() -> None:
    """A signed token whose `sub` isn't a user id must never be accepted."""
    settings = get_settings()
    now = int(time.time())
    token = jwt.encode(
        {"sub": "admin", "iss": settings.api_jwt_issuer, "aud": settings.api_jwt_audience,
         "iat": now, "exp": now + 60},
        settings.api_jwt_secret,
        algorithm="HS256",
    )  # fmt: skip
    with pytest.raises(InvalidToken, match="numeric"):
        decode_api_token(token, settings)


def test_unknown_routes_and_wrong_methods_use_the_one_error_shape() -> None:
    client = TestClient(app)
    missing = client.get("/api/v1/nope")
    assert missing.status_code == 404 and missing.json() == {
        "detail": "Not Found",
        "code": "not_found",
    }
    wrong = client.post("/health")
    assert wrong.status_code == 405 and wrong.json()["code"] == "method_not_allowed"


# --------------------------------------------------------------------------- the model's edges
def test_calibration_survives_a_round_trip_and_rejects_the_wrong_version(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.model import distribution

    cal = Calibration("9.9.9", "test", {"WR": PositionFit(2.0, 0.3, -1.3, 0.0, 1.3, 0.0, 100)})
    assert Calibration.from_json(cal.to_json()) == cal

    path = tmp_path / "calibration.json"
    path.write_text(cal.to_json(), encoding="utf-8")
    monkeypatch.setattr(distribution, "CALIBRATION_FILE", path)
    assert load_calibration("9.9.9") == cal
    with pytest.raises(RuntimeError, match="re-run the backtest"):
        load_calibration("1.0.0")  # calibration fit for a different model version


def test_a_position_without_a_fit_gets_an_honest_wide_range() -> None:
    cal = Calibration("t", "x", {})
    low, mid, high = apply_range(10.0, "QB", cal)
    assert (low, mid, high) == (4.0, 10.0, 18.0)  # 40% / 100% / 160% + 2


def test_projecting_nobody_returns_an_empty_table_with_the_right_columns() -> None:
    history = pd.DataFrame(
        columns=["gsis_id", "season", "week", "position", "team", "opponent", "points", "snap"]
    )
    targets = pd.DataFrame(columns=["gsis_id", "position", "team", "opponent"])
    out = project_week(history, targets, Context(2026, 5), calibration=None)
    assert out.empty and {"points", "p10", "p50", "p90"} <= set(out.columns)


def test_an_empty_side_scores_zero_in_the_win_simulation() -> None:
    """E.g. an opponent with no starters set: zero points, so any real lineup wins."""
    assert simulate([SimPlayer(8, 12, 18)] * 3, []).win_prob == 1.0
    assert simulate([], [SimPlayer(8, 12, 18)] * 3).win_prob == 0.0


# --------------------------------------------------------------------------- nflverse source
def test_current_season_comes_from_nflverse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nflreadpy, "get_current_season", lambda: 2026)
    assert nflverse.current_season() == 2026


def test_snap_shares_map_pfr_ids_to_gsis_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    snaps = fake.snap_counts(
        [
            {"pfr_player_id": "PuknNa00", "season": 2026, "week": 1, "offense_pct": 0.91},
            {"pfr_player_id": "PuknNa00", "season": 2026, "week": 1, "offense_pct": 0.5},  # dupe
            {"pfr_player_id": "NoMapp00", "season": 2026, "week": 1, "offense_pct": 0.7},
            {"pfr_player_id": "PuknNa00", "season": 2026, "week": 2, "offense_pct": 0.8,
             "game_type": "POST"},  # playoff: excluded
        ]
    )  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_snap_counts", lambda seasons: snaps)
    ids = pl.DataFrame({"pfr_id": ["PuknNa00"], "gsis_id": ["00-1"]})
    out = nflverse.load_snap_shares([2026], ids)
    assert out.select("gsis_id", "week", "offense_pct").rows() == [("00-1", 1, 0.91)]


def test_fetch_frames_gathers_every_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    """One call produces all five frames, in the shape the loader expects."""
    sched = fake.schedules(
        [{"game_id": "g1", "season": 2026, "week": 1, "home_team": "LA", "away_team": "KC",
          "home_score": 24, "away_score": 17}]
    )  # fmt: skip
    stats = fake.player_stats(
        [{"gsis_id": "00-1", "position": "WR", "season": 2026, "week": 1, "team": "LA"}]
    )
    teams = fake.team_stats([{"team": "LA", "opponent_team": "KC", "season": 2026, "week": 1}])
    monkeypatch.setattr(nflreadpy, "load_schedules", lambda s: sched)
    monkeypatch.setattr(nflreadpy, "load_player_stats", lambda s: stats)
    monkeypatch.setattr(nflreadpy, "load_team_stats", lambda s: teams)
    snap_rows = fake.snap_counts(
        [{"pfr_player_id": "A00", "season": 2026, "week": 1, "offense_pct": 0.9}]
    )
    monkeypatch.setattr(nflreadpy, "load_snap_counts", lambda s: snap_rows)
    monkeypatch.setattr(nflreadpy, "load_ff_playerids", lambda: fake.ff_playerids(
        [{"gsis_id": "00-1", "sleeper_id": 100, "pfr_id": "A00"}]
    ))  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_injuries", lambda s: fake.injuries(
        [{"gsis_id": "00-1", "season": 2026, "week": 1, "report_status": "Out"}]
    ))  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_rosters_weekly", lambda s: fake.rosters_weekly(
        [{"gsis_id": "00-1", "season": 2026, "week": 1, "status": "ACT"}]
    ))  # fmt: skip
    frames = ingest.fetch_frames([2026])
    assert frames.schedule.height == 1 and frames.player_stats.height == 1
    assert frames.defense_stats["points_allowed"].to_list() == [17.0]  # LA allowed KC's 17
    assert frames.ids["sleeper_id"].to_list() == ["100"]
    assert frames.snaps["gsis_id"].to_list() == ["00-1"]  # pfr id mapped through the crosswalk
    assert frames.injuries is not None and frames.injuries["report_status"].to_list() == ["Out"]


def test_injury_reports_keep_the_latest_game_status_per_player_week(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Practice days are separate rows; the game designation is the last one filed that week."""
    rows = fake.injuries(
        [
            {"gsis_id": "00-1", "season": 2026, "week": 3, "practice_status": "Limited",
             "date_modified": "2026-09-24T20:00:00Z"},
            {"gsis_id": "00-1", "season": 2026, "week": 3, "report_status": "Questionable",
             "practice_status": "Limited", "date_modified": "2026-09-25T20:00:00Z"},
            {"gsis_id": "00-1", "season": 2026, "week": 3, "report_status": "Out",
             "practice_status": "Did Not Participate", "date_modified": "2026-09-26T20:00:00Z"},
            {"gsis_id": "00-2", "season": 2026, "week": 3, "practice_status": "Full"},
            {"gsis_id": "00-3", "season": 2026, "week": 3, "game_type": "WC",
             "report_status": "Out"},
        ]
    )  # fmt: skip
    monkeypatch.setattr(nflreadpy, "load_injuries", lambda s: rows)
    monkeypatch.setattr(nflreadpy, "load_rosters_weekly", lambda s: fake.rosters_weekly(
        [
            {"gsis_id": "00-1", "season": 2026, "week": 3, "status": "ACT"},
            {"gsis_id": "00-4", "season": 2026, "week": 3, "status": "RES"},  # IR, no report
            {"gsis_id": "00-1", "season": 2026, "week": 4, "status": "RES"},
            {"gsis_id": "00-5", "season": 2026, "week": 3, "status": "CUT"},
            {"gsis_id": "00-6", "season": 2026, "week": 3, "status": "RES", "game_type": "WC"},
        ]
    ))  # fmt: skip
    out = nflverse.load_injury_reports([2026]).sort("gsis_id", "week")
    assert out.select("gsis_id", "week").rows() == [
        ("00-1", 3),
        ("00-1", 4),
        ("00-2", 3),
        ("00-4", 3),
    ]  # playoff and non-reserve roster rows dropped
    assert out["report_status"].to_list() == ["Out", None, None, None]
    assert out["roster_status"].to_list() == [None, "RES", None, "RES"]
    assert out["practice_status"].to_list() == ["Did Not Participate", None, "Full", None]


def test_injury_reports_fail_loudly_when_a_column_disappears(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = fake.injuries([{"gsis_id": "00-1", "season": 2026, "week": 1}]).drop("report_status")
    monkeypatch.setattr(nflreadpy, "load_injuries", lambda s: rows)
    monkeypatch.setattr(nflreadpy, "load_rosters_weekly", lambda s: fake.rosters_weekly([]))
    with pytest.raises(nflverse.NflverseSchemaError):
        nflverse.load_injury_reports([2026])
    ok = fake.injuries([{"gsis_id": "00-1", "season": 2026, "week": 1}])
    no_status = fake.rosters_weekly([{"gsis_id": "00-1", "season": 2026, "week": 1}]).drop("status")
    monkeypatch.setattr(nflreadpy, "load_injuries", lambda s: ok)
    monkeypatch.setattr(nflreadpy, "load_rosters_weekly", lambda s: no_status)
    with pytest.raises(nflverse.NflverseSchemaError):
        nflverse.load_injury_reports([2026])


# --------------------------------------------------------------------------- Sleeper adapter
@pytest.fixture
def api() -> Any:
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        yield router


async def test_unreachable_sleeper_is_a_retryable_error(api: respx.MockRouter) -> None:
    api.get("/state/nfl").mock(side_effect=httpx.ConnectError("no route"))
    adapter = SleeperAdapter(retries=1)
    with pytest.raises(AdapterError, match="unreachable"):
        await adapter.fetch_state()
    await adapter.aclose()


async def test_unknown_league_and_user_are_not_found_not_retried(api: respx.MockRouter) -> None:
    api.get("/league/999").respond(content=b"null", content_type="application/json")
    api.get("/user/ghost").respond(404)
    adapter = SleeperAdapter(retries=2)
    with pytest.raises(NotFoundOnPlatform):
        await adapter.fetch_league("999")
    with pytest.raises(NotFoundOnPlatform):
        await adapter.find_user("ghost")
    assert api.calls.call_count == 2  # no retries for "doesn't exist"
    await adapter.aclose()


async def test_an_empty_player_list_is_a_loud_error_and_non_fantasy_players_are_skipped(
    api: respx.MockRouter,
) -> None:
    adapter = SleeperAdapter(retries=0)
    api.get("/players/nfl").respond(json={})
    with pytest.raises(AdapterSchemaError, match="non-empty"):
        await adapter.fetch_players()

    api.get("/players/nfl").respond(
        json={
            "1": {"player_id": "1", "first_name": "Ana", "last_name": "Cruz", "position": "WR",
                  "team": "WSH", "fantasy_positions": ["WR"]},
            "2": {"player_id": "2", "full_name": "A Linebacker", "position": "LB",
                  "fantasy_positions": ["LB"]},
        }
    )  # fmt: skip
    players = await adapter.fetch_players()
    assert [(p.name, p.nfl_team) for p in players] == [
        ("Ana Cruz", "WAS")
    ]  # name built, team canonical
    await adapter.aclose()
