"""FastAPI dependencies for authentication (who are you?) and tenancy (may you see this?).

Every user-owned route depends on `current_user`. Every league-scoped route goes through
`require_membership`, which returns 404 (not 403) for leagues the user doesn't follow, so the
API never confirms that someone else's league exists (docs/Concepts/Multi-Tenancy.md).
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import InvalidToken, decode_api_token
from app.config import Settings, get_settings
from app.db.models import League, LeagueMembership, User
from app.db.session import get_db
from app.errors import ApiError, NotFound, Unauthorized

DB = Annotated[AsyncSession, Depends(get_db)]


def _bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise Unauthorized()
    return token


async def current_user(
    request: Request, db: DB, settings: Annotated[Settings, Depends(get_settings)]
) -> User:
    try:
        user_id = decode_api_token(_bearer_token(request), settings)
    except InvalidToken as exc:
        raise Unauthorized("Invalid or expired token", code="invalid_token") from exc
    user = await db.get(User, user_id)
    if user is None:  # signed by us, but the account was deleted since
        raise Unauthorized("Account no longer exists", code="invalid_token")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def get_membership(db: AsyncSession, user: User, league_id: int) -> LeagueMembership:
    """The ownership helper: the user's membership in a league, or 404."""
    membership = await db.scalar(
        select(LeagueMembership).where(
            LeagueMembership.user_id == user.id, LeagueMembership.league_id == league_id
        )
    )
    if membership is None:
        raise NotFound("League not found", code="league_not_found")
    return membership


async def require_membership(league_id: int, user: CurrentUser, db: DB) -> LeagueMembership:
    """Path-parameter dependency for /leagues/{league_id}/... routes."""
    return await get_membership(db, user, league_id)


async def require_data_membership(
    membership: Annotated[LeagueMembership, Depends(require_membership)], db: DB
) -> LeagueMembership:
    """For routes that return a league's data: also requires this user's own platform login to
    still work. A user whose ESPN cookies were refused is asked to reconnect and sees nothing
    fetched with a league-mate's login (ADR-051)."""
    from app.services.credentials import has_working_access  # late: avoids an import cycle

    if not await has_working_access(db, membership):
        raise ApiError(
            409,
            "credentials_expired",
            "Your ESPN sign-in expired. Reconnect ESPN to see this league.",
        )
    return membership


async def require_league(
    membership: Annotated[LeagueMembership, Depends(require_data_membership)], db: DB
) -> League:
    league = await db.get(League, membership.league_id)
    assert league is not None  # FK guarantees it
    return league


Membership = Annotated[LeagueMembership, Depends(require_membership)]
DataMembership = Annotated[LeagueMembership, Depends(require_data_membership)]
