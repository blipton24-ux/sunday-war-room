"""Connecting ESPN through the API and worker (P3 steps 9-11, ADR-051/052).

Link first (public leagues need nothing), then cookies for private ones. Covers: cookies stored
encrypted and never queued, returned or echoed; a user's own cookies only; expired cookies
pausing that user's view; the hourly sync skipping unreadable leagues; and the live tick's
credential handling. The queue is faked and worker jobs are run directly, as in
test_league_endpoints.py.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import AuthRequired, CredentialsInvalid, NotFoundOnPlatform
from app.adapters.espn import EspnCredentials, EspnHttp, adapter_factory
from app.crypto import get_cipher
from app.db.models import League, LeagueMembership, NflGame, PlatformAccount, SyncRun, Team
from app.jobs.league_jobs import (
    connect_espn,
    probe_espn,
    sync_all_leagues,
    sync_league_job,
)
from app.main import app
from app.queue import get_queue
from app.services.live import live_update
from tests import espn_fixtures as fx
from tests.conftest import auth_headers, make_user

pytestmark = pytest.mark.integration

LINK = f"https://fantasy.espn.com/football/league?leagueId={fx.PUBLIC_LEAGUE}"
PRIVATE_LINK = f"https://fantasy.espn.com/football/team?leagueId={fx.PRIVATE_LEAGUE}&teamId=7"
COOKIES = {"espn_s2": fx.GOOD_S2, "swid": fx.GOOD_SWID}


class FakeQueue:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, tuple[Any, ...], str | None]] = []

    async def enqueue_job(self, function: str, *args: Any, _job_id: str | None = None) -> None:
        self.jobs.append((function, args, _job_id))


JOBS: dict[str, Callable[..., Awaitable[Any]]] = {
    "connect_espn": connect_espn,
    "probe_espn": probe_espn,
    "sync_league_job": sync_league_job,
}


@pytest.fixture
async def queue(client: httpx.AsyncClient) -> AsyncIterator[FakeQueue]:
    fake = FakeQueue()
    app.dependency_overrides[get_queue] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_queue, None)


@pytest.fixture
async def espn_ctx(ctx: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    """The worker context with Sleeper AND ESPN served from fixtures."""
    fx.mock_espn(router=ctx["router"])
    http = EspnHttp(retries=0)
    ctx["adapter_factories"] = {"espn": adapter_factory(http)}
    yield ctx
    await http.aclose()


async def run_last(queue: FakeQueue, ctx: dict[str, Any]) -> None:
    name, args, _ = queue.jobs[-1]
    await JOBS[name](ctx, *args)


async def job(client: httpx.AsyncClient, h: dict[str, str], job_id: str) -> dict[str, Any]:
    return (await client.get(f"/api/v1/jobs/{job_id}", headers=h)).json()  # type: ignore[no-any-return]


async def probe(
    client: httpx.AsyncClient, queue: FakeQueue, ctx: dict[str, Any], h: dict[str, str], link: str
) -> dict[str, Any]:
    resp = await client.post("/api/v1/platforms/espn/probe", json={"link": link}, headers=h)
    assert resp.status_code == 202, resp.text
    await run_last(queue, ctx)
    return await job(client, h, resp.json()["job_id"])


async def connect_with_cookies(
    client: httpx.AsyncClient, queue: FakeQueue, ctx: dict[str, Any], h: dict[str, str]
) -> dict[str, Any]:
    resp = await client.post("/api/v1/platforms/espn/credentials", json=COOKIES, headers=h)
    assert resp.status_code == 202, resp.text
    await run_last(queue, ctx)
    return await job(client, h, resp.json()["job_id"])


async def follow(client: httpx.AsyncClient, h: dict[str, str], league_id: str) -> httpx.Response:
    return await client.post(
        "/api/v1/leagues", json={"platform": "espn", "external_id": league_id}, headers=h
    )


# --------------------------------------------------------------------------- public: link only
async def test_a_public_league_connects_from_a_pasted_link_with_no_cookies(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    user = await make_user(db, "ana@example.com")
    h = auth_headers(user.id)

    status = await probe(client, queue, espn_ctx, h, LINK)
    assert queue.jobs[-1][0] == "probe_espn" and queue.jobs[-1][1][2:] == ("424242", None)
    assert status["status"] == "done" and status["result"]["public"] is True
    assert [t["name"] for t in status["result"]["teams"]] == [
        "Team 1", "Team 2", "Team 3", "Gridiron Gang",
    ]  # fmt: skip

    resp = await follow(client, h, fx.PUBLIC_LEAGUE)
    assert resp.status_code == 202, resp.text
    membership = await db.scalar(select(LeagueMembership))
    assert membership is not None and membership.platform_account_id is None  # no login needed

    await run_last(queue, espn_ctx)  # the first sync
    league = (await client.get("/api/v1/leagues", headers=h)).json()[0]
    assert (league["platform"], league["name"], league["needs_reconnect"]) == (
        "espn", "ESPN Fixture League", False,
    )  # fmt: skip
    assert league["sync_status"] == "done"
    teams = (await client.get(f"/api/v1/leagues/{league['id']}/teams", headers=h)).json()
    assert len(teams) == 4
    mine = next(t for t in teams if t["name"] == "Team 2")
    resp = await client.patch(
        f"/api/v1/leagues/{league['id']}", json={"my_team_id": mine["id"]}, headers=h
    )
    assert resp.status_code == 200


async def test_a_private_league_link_says_so_and_asks_for_cookies(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    user = await make_user(db, "ana@example.com")
    h = auth_headers(user.id)
    status = await probe(client, queue, espn_ctx, h, PRIVATE_LINK)
    assert status["status"] == "done" and status["result"]["private"] is True
    assert "leagues" not in status["result"]
    assert (await follow(client, h, fx.PRIVATE_LEAGUE)).status_code == 404  # nothing offered yet


async def test_a_league_we_cannot_score_is_explained_not_failed(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    user = await make_user(db, "ana@example.com")
    status = await probe(client, queue, espn_ctx, auth_headers(user.id), fx.CATEGORY_LEAGUE)
    assert status["status"] == "done"
    assert "head-to-head points" in status["result"]["unsupported"]


async def test_an_unknown_league_fails_the_probe_with_a_clear_error(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    user = await make_user(db, "ana@example.com")
    h = auth_headers(user.id)
    resp = await client.post("/api/v1/platforms/espn/probe", json={"link": "1"}, headers=h)
    with pytest.raises(NotFoundOnPlatform):
        await run_last(queue, espn_ctx)
    status = await job(client, h, resp.json()["job_id"])
    assert status["status"] == "failed" and "NotFoundOnPlatform" in status["error"]


async def test_bad_links_are_explained(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue
) -> None:
    user = await make_user(db, "ana@example.com")
    resp = await client.post(
        "/api/v1/platforms/espn/probe",
        json={"link": "https://example.com/not-espn"},
        headers=auth_headers(user.id),
    )
    assert resp.status_code == 422 and resp.json()["code"] == "invalid_league_link"
    assert queue.jobs == []


# --------------------------------------------------------------------------- private: cookies
async def test_cookies_connect_a_private_league_and_are_never_exposed(
    client: httpx.AsyncClient,
    db: AsyncSession,
    queue: FakeQueue,
    espn_ctx: dict[str, Any],
) -> None:
    user = await make_user(db, "ana@example.com")
    h = auth_headers(user.id)

    status = await connect_with_cookies(client, queue, espn_ctx, h)
    # the queue carries the account id only: job arguments sit unencrypted in Redis
    assert fx.GOOD_S2 not in repr(queue.jobs) and fx.GOOD_SWID not in repr(queue.jobs)
    assert status["status"] == "done" and status["result"]["via"] == "cookies"
    leagues = {lg["external_id"]: lg for lg in status["result"]["leagues"]}
    assert set(leagues) == {fx.PUBLIC_LEAGUE, fx.PRIVATE_LEAGUE}  # football, this season only
    assert leagues[fx.PRIVATE_LEAGUE]["team_id"] == "2"  # ESPN says which team is mine

    account = await db.scalar(select(PlatformAccount).where(PlatformAccount.platform == "espn"))
    assert account is not None and account.status == "ok" and account.credentials_checked_at
    assert account.credentials_encrypted and fx.GOOD_S2 not in account.credentials_encrypted
    stored = EspnCredentials.from_json(get_cipher().decrypt(account.credentials_encrypted))
    assert stored == EspnCredentials(fx.GOOD_S2, fx.GOOD_SWID)

    me = (await client.get("/api/v1/me", headers=h)).json()
    assert me["platforms"] == [{"platform": "espn", "display_name": None, "status": "ok"}]
    for text in (str(me), status["result"].__repr__(), str(status)):
        assert fx.GOOD_S2 not in text and "credentials" not in text.lower()

    assert (await follow(client, h, fx.PRIVATE_LEAGUE)).status_code == 202
    membership = await db.scalar(select(LeagueMembership))
    assert membership is not None and membership.platform_account_id == account.id
    await run_last(queue, espn_ctx)  # reads the private league with the user's own cookies
    league = (await client.get("/api/v1/leagues", headers=h)).json()[0]
    assert league["sync_status"] == "done" and league["name"] == "ESPN Private League"


async def test_a_private_league_cannot_be_synced_without_its_cookies(
    db: AsyncSession, espn_ctx: dict[str, Any]
) -> None:
    from app.jobs.tracking import create_run

    league = League(platform="espn", external_id=fx.PRIVATE_LEAGUE, season=2026, name="x")
    user = await make_user(db, "ana@example.com")
    db.add(league)
    await db.commit()
    db.add(LeagueMembership(user_id=user.id, league_id=league.id))  # followed with no cookies
    await db.commit()
    league_id = league.id
    run = await create_run(db, "sync_league", league_id=league_id)
    run_id = run.id
    with pytest.raises(AuthRequired, match="private"):
        await sync_league_job(espn_ctx, run_id, league_id)
    db.expire_all()  # the job updated the run from its own session
    failed = await db.get(SyncRun, run_id)
    assert failed is not None and failed.status == "failed"  # not retried: retrying can't help


@pytest.mark.parametrize(
    "body",
    [
        {"espn_s2": "too-short-value", "swid": fx.GOOD_SWID},  # shorter than a real cookie
        {"espn_s2": "x" * 40, "swid": "not-a-guid-not-a-guid-not-a-guid-12345"},
        {"espn_s2": "has spaces in it " * 3, "swid": fx.GOOD_SWID},
    ],
)
async def test_bad_cookies_are_refused_and_never_echoed(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, body: dict[str, str]
) -> None:
    user = await make_user(db, "ana@example.com")
    resp = await client.post(
        "/api/v1/platforms/espn/credentials", json=body, headers=auth_headers(user.id)
    )
    assert resp.status_code == 422
    for secret in body.values():
        assert secret not in resp.text  # validation errors must not echo what was pasted
    assert queue.jobs == [] and await db.scalar(select(PlatformAccount)) is None


async def test_a_league_offered_to_one_user_cannot_be_followed_by_another(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    ana = await make_user(db, "ana@example.com")
    bob = await make_user(db, "bob@example.com")
    await connect_with_cookies(client, queue, espn_ctx, auth_headers(ana.id))
    resp = await follow(client, auth_headers(bob.id), fx.PRIVATE_LEAGUE)
    assert resp.status_code == 404 and resp.json()["code"] == "league_not_offered"


async def test_reconnecting_replaces_the_stored_cookies(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    user = await make_user(db, "ana@example.com")
    h = auth_headers(user.id)
    await connect_with_cookies(client, queue, espn_ctx, h)
    await db.execute(update(PlatformAccount).values(status="needs_reconnect"))
    await db.commit()
    await connect_with_cookies(client, queue, espn_ctx, h)
    accounts = (await db.scalars(select(PlatformAccount))).all()
    assert len(accounts) == 1 and accounts[0].status == "ok"


# --------------------------------------------------------------------------- expired cookies
async def two_followers(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, ctx: dict[str, Any]
) -> tuple[Any, Any, League]:
    """Ana and Bob both follow the private league with their own (valid) cookies."""
    users = [await make_user(db, f"{n}@example.com") for n in ("ana", "bob")]
    for u in users:
        h = auth_headers(u.id)
        await connect_with_cookies(client, queue, ctx, h)
        assert (await follow(client, h, fx.PRIVATE_LEAGUE)).status_code == 202
    league = await db.scalar(select(League))
    assert league is not None
    # Ana's follow queued the first sync (Bob's reused it): run it, so none stays "queued"
    first_sync = next(args for name, args, _ in queue.jobs if name == "sync_league_job")
    await sync_league_job(ctx, *first_sync)
    return users[0], users[1], league


async def revoke(db: AsyncSession, user_id: int) -> None:
    bad = EspnCredentials(fx.REVOKED_S2, fx.GOOD_SWID)
    await db.execute(
        update(PlatformAccount)
        .where(PlatformAccount.user_id == user_id)
        .values(credentials_encrypted=get_cipher().encrypt(bad.to_json()))
    )
    await db.commit()


async def test_one_members_expired_cookies_pause_only_their_own_view(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    from app.jobs.tracking import create_run

    ana, bob, league = await two_followers(client, db, queue, espn_ctx)
    ana_id, bob_id, league_id = ana.id, bob.id, league.id  # plain ids: sessions expire objects
    await revoke(db, ana_id)
    now = datetime.now(UTC)  # Ana's was checked most recently, so her cookies are tried first
    for user_id, when in ((ana_id, now), (bob_id, now - timedelta(days=1))):
        await db.execute(
            update(PlatformAccount)
            .where(PlatformAccount.user_id == user_id)
            .values(credentials_checked_at=when)
        )
    await db.commit()

    run = await create_run(db, "sync_league", league_id=league_id)
    await sync_league_job(espn_ctx, run.id, league_id)  # Ana's refused, Bob's work: it syncs

    db.expire_all()
    status = {a.user_id: a.status for a in await db.scalars(select(PlatformAccount))}
    assert status == {ana_id: "needs_reconnect", bob_id: "ok"}

    ana_h, bob_h = auth_headers(ana_id), auth_headers(bob_id)
    ana_leagues = (await client.get("/api/v1/leagues", headers=ana_h)).json()
    bob_leagues = (await client.get("/api/v1/leagues", headers=bob_h)).json()
    assert ana_leagues[0]["needs_reconnect"] is True and bob_leagues[0]["needs_reconnect"] is False

    # Ana is asked to reconnect; she is never served data fetched with Bob's login.
    resp = await client.get(f"/api/v1/leagues/{league_id}/lineup", headers=ana_h)
    assert resp.status_code == 409 and resp.json()["code"] == "credentials_expired"
    resp = await client.get(f"/api/v1/leagues/{league_id}/lineup", headers=bob_h)
    assert resp.json().get("code") != "credentials_expired"
    me = (await client.get("/api/v1/me", headers=ana_h)).json()
    assert me["platforms"][0]["status"] == "needs_reconnect"
    # she can still leave the league
    assert (await client.delete(f"/api/v1/leagues/{league_id}", headers=ana_h)).status_code == 204


async def test_when_every_followers_cookies_fail_the_sync_stops_and_the_hourly_cron_skips_it(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    from app.jobs.tracking import create_run

    ana, bob, league = await two_followers(client, db, queue, espn_ctx)
    ana_id, bob_id, league_id = ana.id, bob.id, league.id  # plain ids: sessions expire objects
    await revoke(db, ana_id)
    await revoke(db, bob_id)

    run = await create_run(db, "sync_league", league_id=league_id)
    run_id = run.id
    with pytest.raises(CredentialsInvalid):
        await sync_league_job(espn_ctx, run_id, league_id)
    db.expire_all()
    failed = await db.get(SyncRun, run_id)
    assert failed is not None and failed.status == "failed"  # not retried: retrying can't help
    assert {a.status for a in await db.scalars(select(PlatformAccount))} == {"needs_reconnect"}

    espn_ctx["redis"] = FakeQueue()
    assert await sync_all_leagues(espn_ctx) == 0  # nothing to read the league with
    assert espn_ctx["redis"].jobs == []

    # Ana reconnects with working cookies: the league is readable again.
    await connect_with_cookies(client, queue, espn_ctx, auth_headers(ana_id))
    assert await sync_all_leagues(espn_ctx) == 1


async def test_bad_cookies_at_connect_time_mark_the_account_for_reconnect(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    user = await make_user(db, "ana@example.com")
    h = auth_headers(user.id)
    body = {"espn_s2": fx.REVOKED_S2, "swid": fx.GOOD_SWID}
    resp = await client.post("/api/v1/platforms/espn/credentials", json=body, headers=h)
    with pytest.raises(CredentialsInvalid):
        await run_last(queue, espn_ctx)
    status = await job(client, h, resp.json()["job_id"])
    assert status["status"] == "failed" and "CredentialsInvalid" in status["error"]
    assert fx.REVOKED_S2 not in str(status)
    account = await db.scalar(select(PlatformAccount))
    assert account is not None and account.status == "needs_reconnect"


# --------------------------------------------------------------------------- disconnect
async def test_disconnect_forgets_the_cookies(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    user = await make_user(db, "ana@example.com")
    h = auth_headers(user.id)
    await connect_with_cookies(client, queue, espn_ctx, h)
    assert (await client.delete("/api/v1/platforms/espn", headers=h)).status_code == 204
    assert await db.scalar(select(PlatformAccount)) is None  # nothing used it: removed outright
    assert (
        await client.delete("/api/v1/platforms/espn", headers=h)
    ).status_code == 204  # idempotent


async def test_disconnect_keeps_followed_leagues_but_wipes_the_cookies(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    user = await make_user(db, "ana@example.com")
    h = auth_headers(user.id)
    await connect_with_cookies(client, queue, espn_ctx, h)
    await follow(client, h, fx.PRIVATE_LEAGUE)
    assert (await client.delete("/api/v1/platforms/espn", headers=h)).status_code == 204
    db.expire_all()
    account = await db.scalar(select(PlatformAccount))
    assert account is not None
    assert account.credentials_encrypted is None and account.status == "needs_reconnect"
    league = (await client.get("/api/v1/leagues", headers=h)).json()[0]
    assert league["needs_reconnect"] is True


async def test_a_job_for_someone_elses_account_is_refused(
    client: httpx.AsyncClient, db: AsyncSession, queue: FakeQueue, espn_ctx: dict[str, Any]
) -> None:
    from app.jobs.tracking import create_run

    ana = await make_user(db, "ana@example.com")
    bob = await make_user(db, "bob@example.com")
    ana_id, bob_id = ana.id, bob.id
    resp = await client.post(
        "/api/v1/platforms/espn/credentials", json=COOKIES, headers=auth_headers(ana_id)
    )
    assert resp.status_code == 202
    account_id = queue.jobs[-1][1][2]  # the account id is all the queue carries
    run = await create_run(db, "espn_connect", requested_by=bob_id)
    with pytest.raises(LookupError, match="not found"):
        await connect_espn(espn_ctx, run.id, bob_id, account_id)  # Bob can't use Ana's login


# --------------------------------------------------------------------------- live job
async def test_the_live_job_reads_with_a_followers_cookies_and_marks_refused_ones(
    client: httpx.AsyncClient,
    db: AsyncSession,
    queue: FakeQueue,
    espn_ctx: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.jobs import league_jobs
    from app.jobs.league_jobs import live_update_job

    ana, bob, _league = await two_followers(client, db, queue, espn_ctx)
    ana_id, bob_id = ana.id, bob.id
    kickoff = datetime.now(UTC) - timedelta(hours=1)  # a game is on right now
    db.add(NflGame(game_id="g9", season=2026, week=9, home="KC", away="DEN", kickoff_at=kickoff))
    await db.commit()

    async def no_scoreboard(season: int, week: int) -> list[Any]:
        return []

    monkeypatch.setattr(league_jobs, "fetch_week", no_scoreboard)

    assert (await live_update_job(espn_ctx))["leagues"] == 1  # read with a follower's cookies

    await revoke(db, ana_id)
    await revoke(db, bob_id)
    # each tick tries the best candidate; a refusal marks that account and the next tick moves on
    assert (await live_update_job(espn_ctx))["leagues"] == 0
    assert (await live_update_job(espn_ctx))["leagues"] == 0
    db.expire_all()
    assert {a.status for a in await db.scalars(select(PlatformAccount))} == {"needs_reconnect"}
    assert (await live_update_job(espn_ctx))["leagues"] == 0  # nobody left to read it with


# --------------------------------------------------------------------------- live tick
class _Stub:
    """A league reader whose login ESPN has just refused."""

    async def fetch_matchups(self, *_: Any) -> list[Any]:
        raise CredentialsInvalid("refused")


async def live_league(db: AsyncSession) -> int:
    """A followed ESPN league with a game on right now; returns its id."""
    league = League(platform="espn", external_id=fx.PRIVATE_LEAGUE, season=2026, name="Live")
    user = await make_user(db, "live@example.com")
    db.add(league)
    await db.commit()
    league_id = league.id
    db.add(LeagueMembership(user_id=user.id, league_id=league_id))
    kickoff = datetime.now(UTC) - timedelta(hours=1)  # a game is on right now
    db.add(NflGame(game_id="g1", season=2026, week=9, home="KC", away="DEN", kickoff_at=kickoff))
    await db.commit()
    return league_id


async def test_the_live_tick_skips_a_league_with_no_usable_login(
    db: AsyncSession, espn_ctx: dict[str, Any]
) -> None:
    await live_league(db)

    async def nobody(league: League) -> None:
        return None

    async def fetch(season: int, week: int) -> list[Any]:
        return []

    result = await live_update(db, espn_ctx["adapters"]["sleeper"], fetch, resolve=nobody)
    assert result["leagues"] == 0


async def test_the_live_tick_reports_refused_credentials_and_carries_on(
    db: AsyncSession, espn_ctx: dict[str, Any]
) -> None:
    league_id = await live_league(db)
    told: list[int] = []

    async def resolve(lg: League) -> Any:
        return _Stub()

    async def invalid(league_id: int) -> None:
        told.append(league_id)

    async def fetch(season: int, week: int) -> list[Any]:
        return []

    result = await live_update(
        db, espn_ctx["adapters"]["sleeper"], fetch, resolve=resolve, on_invalid=invalid
    )
    assert told == [league_id] and result["leagues"] == 0
    assert await db.scalar(select(Team.id)) is None  # nothing half-written
