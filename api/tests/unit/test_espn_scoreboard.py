"""ESPN scoreboard source against recorded responses (ADR-044).

scoreboard_2026_09 / _10 are real responses (trimmed to the fields we read); the live file is
derived from week 10 with four games set to in progress, halftime, final and end of 1st,
because no game was live when they were recorded.
"""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from app.sources.espn_scoreboard import (
    ScoreboardError,
    ScoreboardSchemaError,
    fetch_week,
    parse_scoreboard,
)

FIX = Path(__file__).parents[1] / "fixtures" / "espn"
BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"


def fx(name: str) -> Any:
    return json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))


def test_finished_week() -> None:
    games = parse_scoreboard(fx("scoreboard_2026_09"))
    assert len(games) == 15
    assert all(g.state == "final" and g.remaining_fraction == 0.0 for g in games)
    assert all(g.home_score is not None and g.away_score is not None for g in games)
    assert all((g.season, g.week) == (2026, 9) for g in games)


def test_upcoming_week_uses_our_team_codes() -> None:
    games = parse_scoreboard(fx("scoreboard_2026_10"))
    assert len(games) == 14  # four teams on bye
    assert all(g.state == "upcoming" and g.remaining_fraction == 1.0 for g in games)
    assert all(g.home_score is None for g in games)
    teams = {t for g in games for t in (g.home, g.away)}
    assert "WAS" in teams and "WSH" not in teams  # ESPN's code mapped to ours
    assert all(g.kickoff_at.tzinfo is not None for g in games)


def test_live_states_and_remaining_time() -> None:
    games = parse_scoreboard(fx("scoreboard_live_derived"))
    live, half, final, end_first = games[:4]  # see the module docstring
    by_state = {"halftime": half, "final": final}
    assert live.period == 3 and live.detail == "4:12 - 3rd"
    assert live.remaining_fraction == pytest.approx((900 + 252) / 3600)
    assert live.possession == live.home and (live.home_score, live.away_score) == (17, 10)
    assert by_state["halftime"].remaining_fraction == 0.5
    assert by_state["final"].remaining_fraction == 0.0
    assert end_first.state == "in_progress" and end_first.remaining_fraction == 0.75
    assert end_first.possession is None


def test_overtime_counts_as_nearly_done() -> None:
    data = fx("scoreboard_live_derived")
    data["events"][0]["status"]["period"] = 5
    data["events"][0]["competitions"][0]["status"]["period"] = 5
    assert parse_scoreboard(data)[0].remaining_fraction == 0.0


def test_postponed_game() -> None:
    data = fx("scoreboard_2026_10")
    for st in (data["events"][0]["status"], data["events"][0]["competitions"][0]["status"]):
        st["type"]["name"] = "STATUS_POSTPONED"
    assert parse_scoreboard(data)[0].state == "postponed"


@pytest.mark.parametrize(
    "breakage",
    ["no_events_key", "no_status", "one_team"],
)
def test_shape_change_fails_loudly(breakage: str) -> None:
    data = fx("scoreboard_2026_09")
    if breakage == "no_events_key":
        del data["events"]
    elif breakage == "no_status":
        del data["events"][0]["status"]
    else:
        data["events"][0]["competitions"][0]["competitors"].pop()
    with pytest.raises(ScoreboardSchemaError):
        parse_scoreboard(data)


async def test_fetch_week_over_http() -> None:
    with respx.mock(base_url=BASE) as router:
        route = router.get("/scoreboard").respond(json=fx("scoreboard_2026_09"))
        games = await fetch_week(2026, 9)
    assert len(games) == 15
    assert dict(route.calls.last.request.url.params) == {
        "seasontype": "2", "week": "9", "dates": "2026"
    }  # fmt: skip


async def test_fetch_week_errors() -> None:
    with respx.mock(base_url=BASE) as router:
        router.get("/scoreboard").respond(status_code=503)
        with pytest.raises(ScoreboardError):
            await fetch_week(2026, 9)
    with respx.mock(base_url=BASE) as router:
        router.get("/scoreboard").mock(side_effect=httpx.ConnectError("down"))
        with pytest.raises(ScoreboardError):
            await fetch_week(2026, 9)
