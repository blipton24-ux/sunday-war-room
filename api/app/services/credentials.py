"""Stored platform credentials: saving them encrypted and choosing whose cookies read a league.

ADR-051/052. A user's cookies are used only for that user's access to a league. A private league's
data is stored once, so some follower's working cookies must fetch it, but the API only shows it
to followers whose own account still works (app/auth/deps.py); a user whose cookies expired sees
a reconnect prompt, never data fetched with someone else's login.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.espn import EspnAccess, EspnCredentials
from app.crypto import get_cipher
from app.db.models import League, LeagueMembership, PlatformAccount
from app.logging import get_logger

log = get_logger("credentials")

OK, PENDING, NEEDS_RECONNECT = "ok", "pending", "needs_reconnect"


async def save_espn_credentials(
    db: AsyncSession, user_id: int, creds: EspnCredentials
) -> PlatformAccount:
    """Encrypt and store a user's ESPN cookies (replacing any earlier ones). Status: pending."""
    account = await db.scalar(
        select(PlatformAccount).where(
            PlatformAccount.user_id == user_id, PlatformAccount.platform == "espn"
        )
    )
    if account is None:
        account = PlatformAccount(user_id=user_id, platform="espn", external_user_id=creds.swid)
        db.add(account)
    account.external_user_id = creds.swid
    account.credentials_encrypted = get_cipher().encrypt(creds.to_json())
    account.status = PENDING
    account.credentials_checked_at = None
    await db.commit()
    return account


def decrypt_espn(account: PlatformAccount) -> EspnCredentials:
    assert account.credentials_encrypted is not None, "account has no stored credentials"
    return EspnCredentials.from_json(get_cipher().decrypt(account.credentials_encrypted))


async def set_status(db: AsyncSession, account: PlatformAccount, status: str) -> None:
    account.status = status
    account.credentials_checked_at = datetime.now(UTC)
    await db.commit()
    if status == NEEDS_RECONNECT:
        log.warning("credentials_need_reconnect", account_id=account.id, platform=account.platform)


@dataclass(frozen=True)
class Candidate:
    """One way to read a league: with a follower's cookies, or with none (a public league)."""

    account: PlatformAccount | None
    access: EspnAccess


async def espn_candidates(db: AsyncSession, league: League) -> list[Candidate]:
    """Who can read this ESPN league, best first: followers with working cookies, newest check
    first. A league nobody connected cookies for is public: one candidate with no cookies. A
    private league whose followers all need to reconnect has no candidate."""
    accounts = (
        await db.scalars(
            select(PlatformAccount)
            .join(
                LeagueMembership,
                LeagueMembership.platform_account_id == PlatformAccount.id,
            )
            .where(LeagueMembership.league_id == league.id)
        )
    ).all()
    if not accounts:
        return [Candidate(None, EspnAccess(league.season, None))]
    working = [a for a in accounts if a.status != NEEDS_RECONNECT and a.credentials_encrypted]
    working.sort(key=lambda a: a.credentials_checked_at or datetime.min.replace(tzinfo=UTC))
    working.reverse()
    return [Candidate(a, EspnAccess(league.season, decrypt_espn(a))) for a in working]


async def has_working_access(db: AsyncSession, membership: LeagueMembership) -> bool:
    """False when this follower's own cookies for the league were refused (reconnect needed)."""
    if membership.platform_account_id is None:
        return True
    account = await db.get(PlatformAccount, membership.platform_account_id)
    return account is None or account.status != NEEDS_RECONNECT
