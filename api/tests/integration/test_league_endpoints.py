"""Onboarding through the API: connect Sleeper -> follow a league -> pick my team -> refresh.

The queue is faked (records enqueues); worker jobs are invoked directly where a test needs
their result. test_sync_and_jobs.py covers the real Redis path.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SyncRun, Team
from app.jobs.league_jobs import connect_sleeper, sync_league_job
from app.main import app
from app.queue import get_queue
from tests.conftest import auth_headers, make_user
from tests.sleeper_fixtures import LEAGUE_ID

pytestmark = pytest.mark.integration


class FakeQueue:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, tuple[Any, ...], str | None]] = []

    async def enqueue_job(self, function: str, *args: Any, _job_id: str | None = None) -> None:
        self.jobs.append((function, args, _job_id))


@pytest.fixture
async def queue(client: httpx.AsyncClient) -> AsyncIterator[FakeQueue]:
    fake = FakeQueue()
    app.dependency_overrides[get_queue] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_queue, None)


async def run_job(queue: FakeQueue, ctx: dict[str, Any]) -> None:
    """Pretend to be the worker: run the most recent enqueued job."""
    name, args, _ = queue.jobs[-1]
    jobs: dict[str, Callable[..., Awaitable[Any]]] = {
        "connect_sleeper": connect_sleeper,
        "sync_league_job": sync_league_job,
    }
    fn = jobs[name]
    await fn(ctx, *args)


async def test_full_onboarding_flow(
    client: httpx.AsyncClient,
    db: AsyncSession,
    queue: FakeQueue,
    ctx: dict[str, Any],
) -> None:
    worker = ctx
    user = await make_user(db, "ana@example.com")
    h = auth_headers(user.id)

    # 1. Connect: 202 + job id; the worker finds the leagues.
    resp = await client.post(
        "/api/v1/platforms/sleeper/connect", json={"username": "fixtureuser"}, headers=h
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    assert queue.jobs[-1][0] == "connect_sleeper"
    status = (await client.get(f"/api/v1/jobs/{job_id}", headers=h)).json()
    assert status["status"] == "queued"

    await run_job(queue, worker)
    status = (await client.get(f"/api/v1/jobs/{job_id}", headers=h)).json()
    assert status["status"] == "done"
    assert status["result"]["leagues"][0]["external_id"] == LEAGUE_ID

    # 2. Follow: league appears at once (stub), sync is queued.
    resp = await client.post(
        "/api/v1/leagues", json={"platform": "sleeper", "external_id": LEAGUE_ID}, headers=h
    )
    assert resp.status_code == 202, resp.text
    league = resp.json()["league"]
    assert league["sync_status"] == "queued" and league["last_synced_at"] is None
    await run_job(queue, worker)

    leagues = (await client.get("/api/v1/leagues", headers=h)).json()
    assert [lg["name"] for lg in leagues] == ["Fixture League"]
    assert leagues[0]["sync_status"] == "done" and leagues[0]["current_week"] == 9

    # 3. Pick my team.
    lid = league["id"]
    teams = (await client.get(f"/api/v1/leagues/{lid}/teams", headers=h)).json()
    assert len(teams) == 12
    team1 = next(t for t in teams if t["name"] == "Team 1")
    resp = await client.patch(f"/api/v1/leagues/{lid}", json={"my_team_id": team1["id"]}, headers=h)
    assert resp.status_code == 200 and resp.json()["my_team_id"] == team1["id"]
    me = (await client.get("/api/v1/me", headers=h)).json()
    assert me["sleeper_username"] == "fixtureuser"
    assert me["memberships"][0]["my_team_id"] == team1["id"]

    # 4. Refresh right after a sync this user asked for: rate limited.
    resp = await client.post(f"/api/v1/leagues/{lid}/refresh", headers=h)
    assert resp.status_code == 429 and resp.json()["code"] == "rate_limited"

    # 5. Unfollow.
    assert (await client.delete(f"/api/v1/leagues/{lid}", headers=h)).status_code == 204
    assert (await client.get("/api/v1/leagues", headers=h)).json() == []


async def test_cannot_follow_a_league_not_offered_by_connect(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue
) -> None:
    user = await make_user(db, "ana@example.com")
    resp = await client.post(
        "/api/v1/leagues",
        json={"platform": "sleeper", "external_id": "424242"},
        headers=auth_headers(user.id),
    )
    assert resp.status_code == 404 and resp.json()["code"] == "league_not_offered"
    assert queue.jobs == []


async def test_refresh_reuses_a_sync_already_in_flight(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue
) -> None:
    from app.db.models import League, LeagueMembership

    a = await make_user(db, "a@example.com")
    b = await make_user(db, "b@example.com")
    league = League(platform="sleeper", external_id="1", season=2026, name="Shared")
    db.add(league)
    await db.flush()
    db.add_all(
        [
            LeagueMembership(user_id=a.id, league_id=league.id),
            LeagueMembership(user_id=b.id, league_id=league.id),
        ]
    )
    await db.commit()

    first = await client.post(f"/api/v1/leagues/{league.id}/refresh", headers=auth_headers(a.id))
    second = await client.post(f"/api/v1/leagues/{league.id}/refresh", headers=auth_headers(b.id))
    assert first.status_code == second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]
    assert len(queue.jobs) == 1
    # A league-mate can see the shared sync job; a stranger cannot.
    stranger = await make_user(db, "c@example.com")
    job = first.json()["job_id"]
    assert (await client.get(f"/api/v1/jobs/{job}", headers=auth_headers(b.id))).status_code == 200
    resp = await client.get(f"/api/v1/jobs/{job}", headers=auth_headers(stranger.id))
    assert resp.status_code == 404


async def test_my_team_must_belong_to_the_league(
    client: httpx.AsyncClient, db: AsyncSession
) -> None:
    from app.db.models import League, LeagueMembership

    user = await make_user(db, "a@example.com")
    mine = League(platform="sleeper", external_id="1", season=2026, name="Mine")
    other = League(platform="sleeper", external_id="2", season=2026, name="Other")
    db.add_all([mine, other])
    await db.flush()
    foreign_team = Team(league_id=other.id, external_id="1", name="Not yours")
    db.add_all([LeagueMembership(user_id=user.id, league_id=mine.id), foreign_team])
    await db.commit()

    resp = await client.patch(
        f"/api/v1/leagues/{mine.id}",
        json={"my_team_id": foreign_team.id},
        headers=auth_headers(user.id),
    )
    assert resp.status_code == 422 and resp.json()["code"] == "invalid_team"


async def test_connect_validates_username(client: httpx.AsyncClient, db: AsyncSession) -> None:
    user = await make_user(db, "a@example.com")
    resp = await client.post(
        "/api/v1/platforms/sleeper/connect",
        json={"username": "../../etc"},
        headers=auth_headers(user.id),
    )
    assert resp.status_code == 422 and resp.json()["code"] == "invalid"
    assert (await db.scalars(select(SyncRun))).all() == []
