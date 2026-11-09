"""The API's handle on the Redis job queue. Routes depend on `get_queue`; tests override it."""

from __future__ import annotations

from typing import Any, Protocol

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings


class Queue(Protocol):
    async def enqueue_job(self, function: str, *args: Any, _job_id: str | None = None) -> Any: ...


_pool: ArqRedis | None = None


async def get_queue() -> Queue:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool


async def close_queue() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
