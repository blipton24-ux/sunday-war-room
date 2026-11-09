# syntax=docker/dockerfile:1
#
# Sunday War Room API image (ADR-020). ONE image, two roles:
#   docker run <image>                              the HTTP API (default command)
#   docker run <image> arq app.worker.WorkerSettings    the background worker
#   docker run <image> alembic upgrade head          the database migration
# Python packages come from uv.lock, so the image installs exactly what was tested.
# Health checks live in docker-compose.yml, per role, because the worker has no HTTP port.

FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# ---- dependencies (cached until pyproject.toml or uv.lock change)
FROM base AS deps
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# ---- the same plus the test tools: `docker build --target test`
FROM deps AS test-deps
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --extra dev

FROM base AS test
COPY --from=test-deps /app/.venv /app/.venv
COPY pyproject.toml alembic.ini openapi.json ./
COPY app ./app
COPY alembic ./alembic
COPY tests ./tests
CMD ["pytest", "-q"]

# ---- production image (the default target)
FROM base AS runtime
RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --no-create-home --shell /usr/sbin/nologin app
COPY --from=deps /app/.venv /app/.venv
COPY alembic.ini ./
COPY app ./app
COPY alembic ./alembic
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
