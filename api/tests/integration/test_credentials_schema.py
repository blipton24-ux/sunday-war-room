"""The P3 credentials columns and the rotation script (step 4)."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.crypto import CredentialCipher
from app.db.models import League, LeagueMembership, PlatformAccount
from tests.conftest import make_user

pytestmark = pytest.mark.integration


async def test_new_accounts_start_ok_with_no_credentials(db: AsyncSession) -> None:
    user = await make_user(db, "a@example.com")
    db.add(PlatformAccount(user_id=user.id, platform="sleeper", external_user_id="1"))
    await db.commit()
    account = await db.scalar(select(PlatformAccount))
    assert account is not None
    assert (account.status, account.credentials_encrypted) == ("ok", None)
    assert account.credentials_checked_at is None


async def test_deleting_an_account_keeps_the_follow_but_clears_its_credentials_link(
    db: AsyncSession,
) -> None:
    user = await make_user(db, "b@example.com")
    league = League(platform="espn", external_id="1", season=2026, name="L")
    account = PlatformAccount(user_id=user.id, platform="espn", external_user_id="{X}")
    db.add_all([league, account])
    await db.commit()
    db.add(LeagueMembership(user_id=user.id, league_id=league.id, platform_account_id=account.id))
    await db.commit()

    await db.delete(account)
    await db.commit()
    membership = await db.scalar(select(LeagueMembership))
    assert membership is not None and membership.platform_account_id is None


async def test_rotate_script_reencrypts_with_the_newest_key(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.scripts import rotate_credentials

    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    user = await make_user(db, "c@example.com")
    stored = CredentialCipher([old]).encrypt("cookies")
    db.add(
        PlatformAccount(
            user_id=user.id, platform="espn", external_user_id="{Y}", credentials_encrypted=stored
        )
    )
    await db.commit()

    both = CredentialCipher([new, old])
    monkeypatch.setattr(rotate_credentials, "get_cipher", lambda: both)
    monkeypatch.setattr(
        rotate_credentials,
        "get_sessionmaker",
        lambda: async_sessionmaker(db.bind, expire_on_commit=False),
    )
    monkeypatch.setattr(rotate_credentials, "get_engine", lambda: db.bind)

    assert await rotate_credentials.rotate(dry_run=True) == {"rotated": 1, "failed": 0}
    db.expire_all()
    assert (await db.scalar(select(PlatformAccount.credentials_encrypted))) == stored  # untouched

    assert await rotate_credentials.rotate() == {"rotated": 1, "failed": 0}
    db.expire_all()
    fresh = await db.scalar(select(PlatformAccount.credentials_encrypted))
    assert fresh is not None and fresh != stored
    assert CredentialCipher([new]).decrypt(fresh) == "cookies"
