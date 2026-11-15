"""Re-encrypt every stored credential with the newest key (ADR-052).

To rotate: generate a new key, put it FIRST in CREDENTIALS_KEYS (keep the old one after it),
deploy, run this script, then drop the old key once it reports nothing left to rotate.

    python -m app.scripts.rotate_credentials [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.crypto import CredentialError, get_cipher
from app.db.models import PlatformAccount
from app.db.session import get_engine, get_sessionmaker


async def rotate(*, dry_run: bool = False) -> dict[str, int]:
    cipher = get_cipher()
    counts = {"rotated": 0, "failed": 0}
    async with get_sessionmaker()() as db:
        rows = await db.scalars(
            select(PlatformAccount).where(PlatformAccount.credentials_encrypted.is_not(None))
        )
        for account in rows:
            assert account.credentials_encrypted is not None
            try:
                fresh = cipher.rotate(account.credentials_encrypted)
            except CredentialError:
                counts["failed"] += 1  # reported by id only; the value is never printed
                print(f"could not decrypt platform_accounts.id={account.id}")
                continue
            if fresh != account.credentials_encrypted:
                counts["rotated"] += 1
                if not dry_run:
                    account.credentials_encrypted = fresh
        if not dry_run:
            await db.commit()
    await get_engine().dispose()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="count, but change nothing")
    args = parser.parse_args()
    print(asyncio.run(rotate(dry_run=args.dry_run)))


if __name__ == "__main__":
    main()
