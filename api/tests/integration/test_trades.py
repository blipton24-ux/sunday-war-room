"""Trade analyzer endpoints on the fixture league (P2 step 5, ADR-048)."""

from typing import Any

import httpx
import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LeagueMembership
from app.model.value import starting_slots
from tests.conftest import auth_headers, make_user

pytestmark = pytest.mark.integration


def url(league_id: int, path: str) -> str:
    return f"/api/v1/leagues/{league_id}/trades/{path}"


async def rosters(client: httpx.AsyncClient, w: dict[str, Any]) -> dict[str, Any]:
    resp = await client.get(url(w["league"].id, "rosters"), headers=auth_headers(w["user"].id))
    assert resp.status_code == 200, resp.text
    body: dict[str, Any] = resp.json()
    return body


async def test_rosters_list_every_team_mine_first(
    projected: dict[str, Any], client: httpx.AsyncClient
) -> None:
    body = await rosters(client, projected)
    assert body["ready"] is True and len(body["teams"]) == 12
    assert body["teams"][0]["is_mine"] and body["teams"][0]["team_id"] == projected["team"].id
    assert sum(t["is_mine"] for t in body["teams"]) == 1
    assert body["league_kind"] == "dynasty"  # labeled: this-season value only
    assert (body["trade_deadline"], body["deadline_passed"]) == (10, False)
    some = body["teams"][0]["players"][0]
    assert some["points_per_week"] >= 0 and some["slot"]


async def test_evaluate_a_trade_both_ways(
    projected: dict[str, Any], client: httpx.AsyncClient
) -> None:
    body = await rosters(client, projected)
    mine, other = body["teams"][0], body["teams"][1]
    give = mine["players"][0]["player"]["player_id"]
    get_two = [p["player"]["player_id"] for p in other["players"][:2]]
    payload = {"team_a_id": mine["team_id"], "team_b_id": other["team_id"],
               "a_gives": [give], "b_gives": get_two}  # fmt: skip
    h = auth_headers(projected["user"].id)
    resp = await client.post(url(projected["league"].id, "evaluate"), json=payload, headers=h)
    assert resp.status_code == 200, resp.text
    ev = resp.json()
    a, b = ev["a"], ev["b"]
    assert [p["player_id"] for p in a["gives"]] == [give]
    assert sorted(p["player_id"] for p in a["gets"]) == sorted(get_two)
    for side in (a, b):
        assert side["change_per_week"] == pytest.approx(
            side["after_per_week"] - side["before_per_week"], abs=0.02
        )
        n_slots = len(starting_slots(projected["league"].roster_slots))
        assert len(side["lineup_before"]) == len(side["lineup_after"]) == n_slots
    # 2-for-1: team A ends up one over its roster limit only if it was full before.
    assert len(a["dropped"]) <= 1 and b["dropped"] == []

    # Swapping who is "A" mirrors the result.
    flipped = {"team_a_id": other["team_id"], "team_b_id": mine["team_id"],
               "a_gives": get_two, "b_gives": [give]}  # fmt: skip
    ev2 = (
        await client.post(url(projected["league"].id, "evaluate"), json=flipped, headers=h)
    ).json()
    assert ev2["a"]["change_per_week"] == b["change_per_week"]
    assert ev2["b"]["change_per_week"] == a["change_per_week"]


@pytest.mark.parametrize(
    "bad",
    [
        {"same_team": True},
        {"empty_side": True},
        {"wrong_owner": True},
    ],
)
async def test_invalid_trades_are_refused(
    projected: dict[str, Any], client: httpx.AsyncClient, bad: dict[str, bool]
) -> None:
    body = await rosters(client, projected)
    mine, other = body["teams"][0], body["teams"][1]
    mp, op = mine["players"][0]["player"]["player_id"], other["players"][0]["player"]["player_id"]
    payload = {"team_a_id": mine["team_id"], "team_b_id": other["team_id"],
               "a_gives": [mp], "b_gives": [op]}  # fmt: skip
    if bad.get("same_team"):
        payload["team_b_id"] = mine["team_id"]
    if bad.get("empty_side"):
        payload["b_gives"] = []
    if bad.get("wrong_owner"):
        payload["a_gives"] = [op]
    resp = await client.post(
        url(projected["league"].id, "evaluate"), json=payload,
        headers=auth_headers(projected["user"].id),
    )  # fmt: skip
    assert resp.status_code == 422 and resp.json()["code"] == "invalid_trade"


async def test_suggestions_help_me_and_respect_the_limit(
    projected: dict[str, Any], client: httpx.AsyncClient
) -> None:
    h = auth_headers(projected["user"].id)
    lid = projected["league"].id
    strict = (await client.get(url(lid, "suggestions?max_loss=0"), headers=h)).json()
    loose = (await client.get(url(lid, "suggestions?max_loss=3"), headers=h)).json()
    assert strict["ready"] and loose["ready"]
    for body, limit in ((strict, 0.0), (loose, 3.0)):
        for idea in body["ideas"]:
            assert idea["my_change_per_week"] > 0
            assert idea["their_change_per_week"] >= -limit
            assert idea["gives"] and idea["gets"]
    assert len(loose["ideas"]) >= len(strict["ideas"])
    again = (await client.get(url(lid, "suggestions?max_loss=3"), headers=h)).json()
    assert again == loose  # served from the per-sync cache
    too_much = await client.get(url(lid, "suggestions?max_loss=10"), headers=h)
    assert too_much.status_code == 422


async def test_trades_need_membership_and_a_team(
    db: AsyncSession, projected: dict[str, Any], client: httpx.AsyncClient
) -> None:
    lid = projected["league"].id
    stranger = await make_user(db, "outsider@example.com")
    for path in ("rosters", "suggestions"):
        resp = await client.get(url(lid, path), headers=auth_headers(stranger.id))
        assert resp.status_code == 404
    await db.execute(update(LeagueMembership).values(my_team_id=None))
    await db.commit()
    resp = await client.get(url(lid, "suggestions"), headers=auth_headers(projected["user"].id))
    assert resp.status_code == 409 and resp.json()["code"] == "team_not_chosen"
