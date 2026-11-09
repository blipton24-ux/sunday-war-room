---
title: "Data ingestion, job queues and Redis"
date: 2026-11-08
tags: [concept, backend, jobs]
---
# Data ingestion, job queues and Redis

**Ingestion** = getting outside data (Sleeper, nflverse, live scores) into your own database.

## Three ways to do it
1. **Pass-through:** fetch from Sleeper on every page load and save nothing. Simple but slow and fragile, it hits rate limits, and the model can't work this way (it needs saved history).
2. **Scheduled cache:** a timer inside the backend runs syncs; pages read only the database. Fast, but jobs die if the program restarts, user-triggered refreshes make the user wait, and it struggles running many jobs on game day.
3. **Scheduled + job queue (Sunday War Room's choice):** jobs go into a **queue**, a to-do list. Separate **worker** processes take jobs off the list and run them.

## The pieces
- **Redis:** a very fast in-memory data store. Here it holds the job to-do list.
- **ARQ:** a Python library that puts jobs on the Redis list, runs workers, schedules recurring jobs ("cron"), and **retries failures** automatically. Built for async Python, so it fits FastAPI.
- **Worker:** the Sunday War Room backend started in "worker mode." It shares all code with the API.

## Side by side: "Refresh my league" on Sunday
```
Pass-through:  click → FastAPI → Sleeper (wait 1-3s) → page        (every view, every user)
Scheduled:     click → FastAPI runs the sync itself (wait) → page
Job queue:     click → FastAPI drops "sync league 10" into Redis → instantly shows "Syncing…"
                 worker picks it up → Sleeper → PostgreSQL → page updates
```

## Sunday War Room's jobs (planned)
| Job | Trigger | Phase |
|---|---|---|
| `sync_league` | User connects/refreshes; hourly | P1 |
| `ingest_nflverse` | Daily in season | P1 |
| `compute_projections` | After ingest/sync; never overwrites a projection after kickoff | P1 |
| `poll_live_scores` | Every ~1 min during games | P2 |
| `send_push_alerts` | On injury/score events | P2 |
| `ingest_news` + `embed_news` | Every ~15 min | P3 |

Related: [ADR-016](../Decisions/ADR-016-Ingestion-Job-Queue.md) · [Backend Basics](Backend-Basics.md) · [Architecture](../Specs/Architecture.md)
