"""Recorded (anonymized) Sleeper responses from a real 12-team, half-PPR 2026 league.

The transactions files are hand-written in the shape documented at docs.sleeper.com (no real
league's transactions were recorded); see Verification Gaps V-33.
"""

import json
from pathlib import Path
from typing import Any

import respx

from app.adapters.sleeper import BASE_URL

FIX = Path(__file__).parent / "fixtures" / "sleeper"
LEAGUE_ID = "1100000000000000001"
ME = "900000000000000001"  # the fixture user's Sleeper id; owns roster 8 ("Team 1")


def fx(name: str) -> Any:
    return json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))


def mock_sleeper() -> respx.MockRouter:
    """A respx router answering every Sleeper call the app makes from the fixtures."""
    router = respx.mock(base_url=BASE_URL, assert_all_called=False)
    router.get("/user/fixtureuser").respond(json=fx("user"))
    router.get("/user/nobody").respond(content=b"null", content_type="application/json")
    router.get(f"/user/{ME}/leagues/nfl/2026").respond(json=fx("user_leagues"))
    router.get(f"/league/{LEAGUE_ID}").respond(json=fx("league"))
    router.get(f"/league/{LEAGUE_ID}/rosters").respond(json=fx("rosters"))
    router.get(f"/league/{LEAGUE_ID}/users").respond(json=fx("league_users"))
    for week in range(1, 19):  # a full season, so past-season leagues can sync every week
        name = f"matchups_{week}" if week in (8, 9) else "matchups_8"
        router.get(f"/league/{LEAGUE_ID}/matchups/{week}").respond(json=fx(name))
    for week in range(1, 19):  # shape from docs.sleeper.com; weeks without moves are empty
        tx = fx(f"transactions_{week}") if week in (8, 9) else []
        router.get(f"/league/{LEAGUE_ID}/transactions/{week}").respond(json=tx)
    router.get("/players/nfl").respond(json=fx("players"))
    router.get("/state/nfl").respond(json=fx("state"))
    return router
