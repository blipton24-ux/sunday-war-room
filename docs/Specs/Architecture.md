---
title: "Architecture"
date: 2026-11-08
tags: [spec, architecture]
---
# Architecture

## System diagram
```
                         ┌──────────────────────────────┐
  Phone / browser ──────▶│ web: Next.js (TypeScript)    │  screens + sign-in (Better Auth);
                         │                              │  /api/v1/* pass-through adds token
  (PWA, service worker)  └──────────────┬───────────────┘
                                        │ REST /api/v1 (generated TS client) + signed token
                         ┌──────────────▼───────────────┐
                         │ api: FastAPI (Python)        │  verifies token, scopes by user_id,
                         │                              │  reads DB, enqueues jobs
                         └───────┬──────────────┬───────┘
                                 │              │ enqueue
                         ┌───────▼──────┐  ┌────▼───────┐
                         │ db: Postgres │  │ redis      │  job queue
                         │ + pgvector   │  └────┬───────┘
                         └───────▲──────┘       │ dequeue
                                 │       ┌──────▼──────────────────────────┐
                                 └───────│ worker: ARQ (same Python code)  │
                                         │ adapters · nflverse · model ·   │
                                         │ scores · push · news (later)    │
                                         └──────┬──────────────────────────┘
                                                ▼
                        Sleeper API · nflverse files · (P2 scores) · (P3 news, Claude API) · (P4 ESPN/Yahoo)
```

## Responsibilities
| Service | Does | Never does |
|---|---|---|
| web | Render screens, sign-in UI, call the API | Touch the DB or third-party APIs |
| api | Auth check, tenant scoping, read DB, enqueue jobs, (P3) run the agent loop | Call platforms during a request (except via jobs) |
| worker | All external fetching, projections, scheduled work | Serve HTTP |
| db | Source of truth | — |
| redis | Job queue (and later, rate-limit counters) | Hold anything that can't be lost |

## Backend code layout (planned)
```
api/app/
  main.py              FastAPI app + routers
  worker.py            ARQ WorkerSettings (jobs + cron)
  config.py            settings from environment variables
  db/                  SQLAlchemy models, session, Alembic env
  auth/                token verification, current_user, ownership helpers
  adapters/            base.py (LeagueAdapter), sleeper.py, (espn.py, yahoo.py)
  sources/nflverse.py  the ONLY module that reads nflverse (schema contracts)
  model/               pure functions: scoring, projection, distribution, lineup
  services/            orchestration: sync_league, compute_projections, matchup
  routers/             HTTP endpoints, thin
  jobs/                ARQ job functions calling services
```
**Pure model code** (no I/O) is separate from fetching and storage, so it's easy to unit test (a lesson from the old project).

## Cross-cutting rules
- **One module per external source**; only it knows that source's URLs and formats.
- **Fail loudly on upstream schema changes**, softly on legitimately missing values.
- **Projections freeze at kickoff**, and every stored projection carries `model_version`.
- **Configuration by environment variables** (12-factor style); `.env.example` documents them.
- **Structured logs** with request/job ids; a `/health` endpoint per service.

Related: [Data Model](Data-Model.md) · [API](API.md) · [ADR-013](../Decisions/ADR-013-Backend-FastAPI.md) · [ADR-016](../Decisions/ADR-016-Ingestion-Job-Queue.md)
