"""Shared test fixtures.

Integration tests run against a real Postgres database (`swr_test`, created by
infra/db-init on first start of the compose `db` service), never the dev database.
The schema is built with the real Alembic migrations, so the migrations are tested too.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://swr:swr@localhost:5432/swr_test"
)
# Make the app (settings, session factory) point at the test database too.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("API_JWT_SECRET", "test-secret-not-for-production")


def _run_alembic(*args: str) -> None:
    from alembic.config import Config

    from alembic import command

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(here, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(here, "alembic"))
    cfg.cmd_opts = type("Opts", (), {"x": [f"url={TEST_DATABASE_URL}"]})()
    getattr(command, args[0])(cfg, *args[1:])


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    """Fresh schema for the test session: downgrade to nothing, then upgrade to head."""
    import asyncio

    await asyncio.to_thread(_run_alembic, "downgrade", "base")
    await asyncio.to_thread(_run_alembic, "upgrade", "head")
    eng = create_async_engine(TEST_DATABASE_URL)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A session on a clean database: every table is truncated before each test."""
    async with engine.begin() as conn:
        tables = (
            await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename <> 'alembic_version'"
                )
            )
        ).scalars()
        names = ", ".join(f'"{t}"' for t in tables)
        if names:
            await conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
