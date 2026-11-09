# api — FastAPI server + ARQ worker

One Python codebase that runs as the API server or the background worker ([ADR-013](../docs/Decisions/ADR-013-Backend-FastAPI.md)).

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

> **Windows note:** on some CPUs the default Polars build hangs at import. If
> `python -c "import polars"` never returns, install the compatibility build:
> `pip install "polars[rtcompat]"`. Docker/Linux is unaffected.

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
