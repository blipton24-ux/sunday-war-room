---
title: "ADR-013: Backend — Python FastAPI"
date: 2026-11-08
tags: [adr, backend]
status: accepted
---
# ADR-013: Backend — Python FastAPI (API server + worker)

## Context
The backend stores data, talks to Sleeper/ESPN/Yahoo, runs the projection model and runs scheduled jobs. The projection model ([ADR-008](ADR-008-Own-Projection-Model.md)) depends on Python data tools (pandas, nflreadpy). What a backend does: [Backend Basics](../Concepts/Backend-Basics.md).

## Options considered (same two jobs traced through each)
**(A)** You open the Week 10 matchup. **(B)** Every Tuesday the app re-syncs rosters and recomputes projections.

| | 1: **Python FastAPI** | 2: All TypeScript | 3: Node API + Python worker |
|---|---|---|---|
| Programs | 2 (Next.js + Python backend) | 1 (Next.js does everything) | 3 |
| (A) | Next.js → FastAPI → DB → JSON | Page's server code → DB | Next.js → Node API → DB |
| (B) | Python worker: Sleeper + nflverse + pandas → DB | TS cron route; model rewritten **without pandas/nflreadpy**; may hit host time limits | Node syncs rosters, *then* Python runs model: they must coordinate |
| Model quality / ease | Best | Hardest | Best |
| Deploy / debug effort | Medium | Lowest | Highest: a bug could be in any of 3 places |
| Architecture fit | Each language does what it's best at | One language, weak data tools | Microservices without a need for them |

## Decision
**Option 1.** One Python codebase (`api/`) that starts in two modes:
- **API server** (FastAPI): answers requests from Next.js.
- **Worker** (ARQ, [ADR-016](ADR-016-Ingestion-Job-Queue.md)): runs scheduled and user-triggered jobs.

Both share the same adapters, model and database code. Next.js is screens only.

## Why
It keeps the centerpiece model in Python, where it's easiest to build well, without Option 3's coordination overhead.

## Trade-offs accepted
Two languages to know, and the API contract between them must be kept in sync (solved by [ADR-014](ADR-014-API-REST-OpenAPI.md)).

Related: [Backend Basics](../Concepts/Backend-Basics.md) · [Architecture](../Specs/Architecture.md) · [ADR-016 Job queue](ADR-016-Ingestion-Job-Queue.md)
