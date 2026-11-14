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
                                         │ ML training · scores · push ·   │
                                         │ news (later)                    │
                                         └──────┬──────────────────────────┘
                                                ▼
                        Sleeper API · ESPN API · nflverse files (stats, lines, injuries) · ESPN scoreboard · (P7 Yahoo) · (P5 news, Claude API)
```

## Responsibilities
| Service | Does | Never does |
|---|---|---|
| web | Render screens, sign-in UI, call the API | Touch the DB or third-party APIs |
| api | Auth check, tenant scoping, read DB, enqueue jobs, (P5) run the agent loop | Call platforms during a request (except via jobs) |
| worker | All external fetching, projections, weekly model retraining (P4), scheduled work | Serve HTTP |
| db | Source of truth | — |
| redis | Job queue (and later, rate-limit counters) | Hold anything that can't be lost |

## Backend code layout
```
api/app/
  main.py              FastAPI app + routers
  worker.py            ARQ WorkerSettings (jobs + cron)
  config.py            settings from environment variables
  db/                  SQLAlchemy models, session, Alembic env
  auth/                token verification, current_user, ownership helpers
  adapters/            base.py (LeagueAdapter), sleeper.py, espn.py, (P7 yahoo.py)
  sources/nflverse.py  the ONLY module that reads nflverse (schema contracts)
  model/               pure functions: scoring, projection, distribution, lineup, win probability,
                       rest of season, waivers and trade value, backtest comparison (compare.py)
  model/ml/            (P4) feature table, XGBoost training, stats-then-score projection
  scripts/             backtest.py (walk-forward backtest and report), OpenAPI export, key rotation
  services/            orchestration: sync_league, compute_projections, matchup
  routers/             HTTP endpoints, thin
  jobs/                ARQ job functions calling services
```
**Pure model code** (no I/O) is separate from fetching and storage, so it's easy to unit test (a lesson from the old project).

## The projection model's moving parts (P4)
The model is a machine-learning pipeline ([ADR-060](../Decisions/ADR-060-P4-Machine-Learning-Stats-Then-Score.md)): the daily nflverse ingest stores stats, lines and injury reports → one feature builder turns stored history into a player-week table (the same code for the backtest and the live compute) → XGBoost models predict each stat → league scoring turns stats into points → projections are stored per scoring setup and frozen at kickoff. A weekly worker job retrains the models after the stats load and replaces the live ones only if they are not worse. How it is graded: [Backtesting and measuring](../Concepts/Backtesting-and-Measuring.md).

## Cross-cutting rules
- **One module per external source**; only it knows that source's URLs and formats.
- **Fail loudly on upstream schema changes**, softly on legitimately missing values.
- **Projections freeze at kickoff**, and every stored projection carries `model_version`.
- **No leakage:** anything that feeds a projection is known before that week's kickoff; a unit test enforces it.
- **Configuration by environment variables** (12-factor style); `.env.example` documents them.
- **Structured logs** with request/job ids; a `/health` endpoint per service.

Related: [Data Model](Data-Model.md) · [API](API.md) · [ADR-013](../Decisions/ADR-013-Backend-FastAPI.md) · [ADR-016](../Decisions/ADR-016-Ingestion-Job-Queue.md)
