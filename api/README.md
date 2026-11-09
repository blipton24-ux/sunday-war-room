# api — FastAPI server + ARQ worker

One Python codebase that runs as the API server or the background worker ([ADR-013](../docs/Decisions/ADR-013-Backend-FastAPI.md)).

## Run it in Docker
`docker compose up --build` from the repo root runs everything; the image is `api/Dockerfile` (one image, three jobs:
the API, the worker, the migration). Backend tests inside the locked image:
```bash
docker build --target test -t swr-api-test api
docker compose up -d db redis     # then, on the compose network:
docker run --rm --network sunday-war-room_default -e ENVIRONMENT=test   -e TEST_DATABASE_URL=postgresql+asyncpg://swr:swr@db:5432/swr_test -e REDIS_URL=redis://redis:6379/0 swr-api-test
```

## Dependencies
`uv.lock` pins every package ([ADR-039](../docs/Decisions/ADR-039-Python-Dependency-Lock-uv.md)). After editing
`pyproject.toml`, regenerate it (in Linux, so the result doesn't depend on your machine):
```bash
docker run --rm -v "$PWD:/work" -w /work python:3.12-slim-bookworm sh -c "pip install uv==0.13.7 && uv lock"
```
`pip install -e ".[dev]"` (below) still works for local development but does not use the lock.

## Local setup
```bash
# from FFCC/: start Postgres (+pgvector) and Redis
docker compose up -d db redis

# from FFCC/api/
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"      # macOS/Linux: .venv/bin/python
.venv/Scripts/alembic upgrade head                   # build the schema in the dev database
.venv/Scripts/uvicorn app.main:app --reload          # http://localhost:8000/health (docs: /docs)
.venv/Scripts/arq app.worker.WorkerSettings          # the background worker (second terminal)
```

## Layout
| Path | What |
|---|---|
| `app/main.py`, `app/routers/` | HTTP endpoints (thin) |
| `app/auth/` | API token verification, `current_user`, league membership checks |
| `app/adapters/` | `LeagueAdapter` interface + `sleeper.py` (only module that talks to Sleeper) |
| `app/services/` | Orchestration, e.g. `sync.py` (adapter output -> Postgres upserts) |
| `app/jobs/`, `app/worker.py` | ARQ jobs + schedule; `sync_runs` tracking and retry policy |
| `app/db/` | SQLAlchemy models + session; migrations in `alembic/` |
| `tests/fixtures/sleeper/` | Recorded, anonymized Sleeper responses from a real league |

> **Windows note:** on some CPUs the default Polars build hangs at import, so `pyproject.toml`
> asks Windows for the compatibility build (`polars[rtcompat]`) automatically. Linux (Docker,
> CI, production) gets the standard one.

## Checks
```bash
.venv/Scripts/python -m pytest          # unit + integration (needs db + redis running)
.venv/Scripts/ruff check . && .venv/Scripts/ruff format --check .
.venv/Scripts/mypy app tests
```
Integration tests use the separate `swr_test` database and rebuild it from the
Alembic migrations on every run, so the migrations are exercised too.

## API contract
`api/openapi.json` is committed and is what the web app's TypeScript client is generated from.
After changing any route, request or response model:
```bash
.venv/Scripts/python -m app.scripts.export_openapi     # rewrite api/openapi.json
cd ../web && npm run generate:api                      # regenerate src/lib/api/schema.d.ts
```
`tests/unit/test_openapi_contract.py` fails if the file is stale, and also checks that every
error response is declared with the one `{detail, code}` shape the API really returns.

## Schema changes
Edit `app/db/models.py`, then:
```bash
.venv/Scripts/alembic revision --autogenerate -m "what changed"
.venv/Scripts/alembic upgrade head
```
`tests/integration/test_schema.py` fails if models and migrations disagree.
