"""The migrated schema matches the models, and core constraints hold."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.db.models import League, LeagueMembership, User

pytestmark = pytest.mark.integration


async def test_migrations_match_models(engine: AsyncEngine) -> None:
    """Autogenerate finds nothing to change: models and migrations agree."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.db.base import Base

    def diff(sync_conn):  # type: ignore[no-untyped-def]
        return compare_metadata(MigrationContext.configure(sync_conn), Base.metadata)

    async with engine.connect() as conn:
        changes = await conn.run_sync(diff)
    assert changes == []


async def test_pgvector_enabled(db: AsyncSession) -> None:
    ext = await db.scalar(text("SELECT extname FROM pg_extension WHERE extname='vector'"))
    assert ext == "vector"


async def test_league_unique_per_platform_season(db: AsyncSession) -> None:
    db.add(League(platform="sleeper", external_id="123", season=2026, name="A"))
    await db.commit()
    db.add(League(platform="sleeper", external_id="123", season=2026, name="dup"))
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_deleting_user_removes_memberships(db: AsyncSession) -> None:
    user = User(email="a@example.com")
    league = League(platform="sleeper", external_id="1", season=2026, name="L")
    db.add_all([user, league])
    await db.flush()
    db.add(LeagueMembership(user_id=user.id, league_id=league.id))
    await db.commit()

    await db.delete(user)
    await db.commit()
    assert (await db.scalars(select(LeagueMembership))).all() == []
    # The league itself is shared data and stays.
    assert (await db.scalars(select(League))).one().name == "L"
