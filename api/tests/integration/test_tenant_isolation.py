"""Tenant isolation: user B can never see user A's league (ADR-019, Multi-Tenancy).

This test discovers every route with a `{league_id}` path parameter, so each new league-scoped
endpoint is covered automatically: it must answer 404 to a signed-in user who doesn't follow
the league, exactly as it would for a league that doesn't exist.
"""

import re

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import League, LeagueMembership
from app.main import app
from tests.conftest import auth_headers, make_user

pytestmark = pytest.mark.integration

# Read from the OpenAPI schema (the public list of every endpoint), not app.routes, whose
# internal structure changes between FastAPI versions.
LEAGUE_ROUTES = sorted(
    (method.upper(), path)
    for path, ops in app.openapi()["paths"].items()
    if "{league_id}" in path
    for method in ops
)


def test_league_routes_were_discovered() -> None:
    """Guard: if discovery breaks, the isolation test must fail, not silently test nothing."""
    assert len(LEAGUE_ROUTES) >= 4, LEAGUE_ROUTES


def _url(path: str, league_id: int) -> str:
    url = path.replace("{league_id}", str(league_id))
    return re.sub(r"\{[^}]+\}", "1", url)  # any other path params


@pytest.mark.parametrize(("method", "path"), LEAGUE_ROUTES)
async def test_other_users_league_is_404(
    client: httpx.AsyncClient, db: AsyncSession, method: str, path: str
) -> None:
    alice = await make_user(db, "alice@example.com")
    bob = await make_user(db, "bob@example.com")
    league = League(platform="sleeper", external_id="A1", season=2026, name="Alice's league")
    db.add(league)
    await db.flush()
    db.add(LeagueMembership(user_id=alice.id, league_id=league.id))
    await db.commit()

    url = _url(path, league.id)
    resp = await client.request(method, url, headers=auth_headers(bob.id), json={})
    assert resp.status_code == 404, f"{method} {url} leaked to a non-member: {resp.status_code}"
    assert resp.json()["code"] == "league_not_found"

    # Same answer as a league that doesn't exist at all: existence isn't revealed.
    missing = await client.request(
        method, _url(path, 999_999), headers=auth_headers(bob.id), json={}
    )
    assert missing.status_code == 404
