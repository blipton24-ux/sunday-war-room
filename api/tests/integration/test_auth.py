"""Token verification and the account endpoints."""

from collections.abc import Callable
from datetime import timedelta

import httpx
import jwt
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import mint_api_token
from app.config import Settings, get_settings
from app.db.models import League, LeagueMembership, User
from tests.conftest import auth_headers, make_user

pytestmark = pytest.mark.integration


async def test_me_requires_a_token(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthorized"


async def test_me_returns_the_signed_in_user(client: httpx.AsyncClient, db: AsyncSession) -> None:
    user = await make_user(db, "ana@example.com")
    resp = await client.get("/api/v1/me", headers=auth_headers(user.id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "ana@example.com"
    assert body["plan"] == "free"
    assert body["memberships"] == []


@pytest.mark.parametrize(
    "make_token",
    [
        pytest.param(
            lambda uid, s: mint_api_token(uid, s, ttl=timedelta(seconds=-60)), id="expired"
        ),
        pytest.param(
            lambda uid, s: jwt.encode(
                {
                    "sub": str(uid),
                    "iss": s.api_jwt_issuer,
                    "aud": s.api_jwt_audience,
                    "iat": 0,
                    "exp": 9999999999,
                },
                "a-different-secret-entirely-0123456789",
                algorithm="HS256",
            ),
            id="wrong-secret",
        ),
        pytest.param(
            lambda uid, s: jwt.encode(
                {
                    "sub": str(uid),
                    "iss": s.api_jwt_issuer,
                    "aud": "someone-else",
                    "iat": 0,
                    "exp": 9999999999,
                },
                s.api_jwt_secret,
                algorithm="HS256",
            ),
            id="wrong-audience",
        ),
        pytest.param(
            lambda uid, s: jwt.encode(
                {
                    "sub": str(uid),
                    "iss": s.api_jwt_issuer,
                    "aud": s.api_jwt_audience,
                    "iat": 0,
                    "exp": 9999999999,
                },
                key="",
                algorithm="none",
            ),
            id="alg-none",
        ),
    ],
)
async def test_bad_tokens_are_rejected(
    client: httpx.AsyncClient, db: AsyncSession, make_token: Callable[[int, Settings], str]
) -> None:
    user = await make_user(db, "ana@example.com")
    token = make_token(user.id, get_settings())
    resp = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_token"


async def test_token_for_deleted_user_is_rejected(
    client: httpx.AsyncClient, db: AsyncSession
) -> None:
    resp = await client.get("/api/v1/me", headers=auth_headers(999))
    assert resp.status_code == 401


async def test_delete_me_removes_account_but_keeps_shared_league(
    client: httpx.AsyncClient, db: AsyncSession
) -> None:
    user = await make_user(db, "ana@example.com")
    league = League(platform="sleeper", external_id="1", season=2026, name="L")
    db.add(league)
    await db.flush()
    db.add(LeagueMembership(user_id=user.id, league_id=league.id))
    await db.commit()

    resp = await client.delete("/api/v1/me", headers=auth_headers(user.id))
    assert resp.status_code == 204
    db.expunge_all()
    assert await db.get(User, user.id) is None
    assert (await db.scalars(select(LeagueMembership))).all() == []
    assert (await db.scalars(select(League))).one() is not None
