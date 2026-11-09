"""FastAPI application: the API server half of the api/ codebase (ADR-013)."""

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import install_error_handlers
from app.logging import configure_logging, get_logger
from app.queue import close_queue
from app.routers import jobs, leagues, me, platforms, views

settings = get_settings()
configure_logging(settings.log_level, json=settings.environment != "development")
log = get_logger("api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_queue()


app = FastAPI(
    lifespan=lifespan,
    title="Sunday War Room API",
    version="0.1.0",
    description="Read-only fantasy football assistant API. All data routes live under /api/v1.",
)
install_error_handlers(app)
for router in (me.router, platforms.router, leagues.router, jobs.router, views.router):
    app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Bind a request id to every log line for this request, and log one summary line."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    log.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        ms=round((time.perf_counter() - start) * 1000, 1),
    )
    return response


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Liveness check (no auth)."""
    return {"status": "ok"}
