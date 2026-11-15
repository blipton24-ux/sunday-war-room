from fastapi import APIRouter, Response
from sqlalchemy import delete, select

from app.auth.deps import DB, CurrentUser
from app.db.models import League, LeagueMembership, PlatformAccount, User
from app.errors import error_responses
from app.schemas import MembershipOut, MeOut, PlatformOut

router = APIRouter(prefix="/api/v1/me", tags=["me"], responses=error_responses())


@router.get("", response_model=MeOut)
async def get_me(user: CurrentUser, db: DB) -> MeOut:
    """The signed-in user and the leagues they follow."""
    rows = (
        await db.execute(
            select(LeagueMembership, League)
            .join(League, League.id == LeagueMembership.league_id)
            .where(LeagueMembership.user_id == user.id)
            .order_by(League.name)
        )
    ).all()
    accounts = (
        await db.scalars(
            select(PlatformAccount)
            .where(PlatformAccount.user_id == user.id)
            .order_by(PlatformAccount.platform)
        )
    ).all()
    sleeper = next((a.display_name for a in accounts if a.platform == "sleeper"), None)
    return MeOut(
        id=user.id,
        email=user.email,
        name=user.name,
        image=user.image,
        plan=user.plan,
        sleeper_username=sleeper,
        # status only: the stored credentials never leave the database
        platforms=[
            PlatformOut(platform=a.platform, display_name=a.display_name, status=a.status)
            for a in accounts
        ],
        memberships=[
            MembershipOut(
                league_id=lg.id,
                league_name=lg.name,
                platform=lg.platform,
                season=lg.season,
                my_team_id=m.my_team_id,
                last_synced_at=lg.last_synced_at,
            )
            for m, lg in rows
        ],
    )


@router.delete("", status_code=204)
async def delete_me(user: CurrentUser, db: DB) -> Response:
    """Delete the account and everything owned by it.

    Memberships, platform links and Auth.js sessions cascade from `users`. Shared league and
    NFL data stay: they belong to no single user.
    """
    await db.execute(delete(User).where(User.id == user.id))
    await db.commit()
    return Response(status_code=204)
