---
title: "ADR-016: Data ingestion — scheduled jobs on a Redis queue"
date: 2026-11-08
tags: [adr, data, backend, jobs]
status: accepted
---
# ADR-016: Data ingestion — scheduled + user-triggered jobs on a Redis queue (ARQ)

## Context
League data (Sleeper, later ESPN/Yahoo), NFL stats (nflverse) and live scores must get into PostgreSQL. The question is *when and how*. Full explanation: [Job Queues and Redis](../Concepts/Job-Queues-and-Redis.md).

| Data | Source | Phase |
|---|---|---|
| Leagues, rosters, matchups | Sleeper API (public, no login) | P1 |
| Player stats/history | nflverse via `nflreadpy` | P1 |
| Live scores | Sleeper / public scoreboard feed | P2 |
| News/injury articles | TBD ([Open Questions](../Specs/Open-Questions.md)) | P5 ([ADR-049](ADR-049-Phases-Reordered-ESPN-First.md)) |
| ESPN, Yahoo leagues | ESPN (cookies), Yahoo (OAuth) | P3 ([ADR-049](ADR-049-Phases-Reordered-ESPN-First.md)) |

## Options considered — "Refresh my league" on a Sunday
```
1 Pass-through:  click → FastAPI → Sleeper (wait 1–3s) → page   (every view, every user)
2 Scheduled:     click → FastAPI runs the sync itself (wait) → page   (hourly timer otherwise)
3 Job queue:     click → FastAPI drops "sync league 10" into Redis → instantly "Syncing…"
                 → worker picks it up → Sleeper → PostgreSQL → page updates
```
| | 1 Pass-through | 2 Scheduled cache | 3 **Scheduled + queue** |
|---|---|---|---|
| Page speed | Slow | Fast | Fast |
| Works if Sleeper is down | ❌ | ✅ | ✅ |
| Supports projection model | ❌ | ✅ | ✅ |
| Live game day + push alerts | ❌ | ⚠️ | ✅ |
| Retries failed jobs | ❌ | ⚠️ hand-built | ✅ built in |
| Extra pieces | none | none | Redis |

## Decision
**Option 3.** Jobs (on a schedule or triggered by a user) go onto a **Redis** queue. **ARQ** (async Python) workers run them with automatic retries. **Pages read only from PostgreSQL**, never from a platform API directly.

## Why
The live dashboard and push notifications ([ADR-007](ADR-007-Feature-Set.md), [ADR-010](ADR-010-PWA.md)) need background work that runs in parallel and retries. Redis is one small addition, and the worker from [ADR-013](ADR-013-Backend-FastAPI.md) becomes the queue worker.

## Trade-offs accepted
One more service to run locally and in the cloud. Data is as fresh as the last sync (shown in the UI as "updated 3 min ago").

Related: [Job Queues and Redis](../Concepts/Job-Queues-and-Redis.md) · [Architecture](../Specs/Architecture.md) · [ADR-006 Adapters](ADR-006-Platform-Adapters.md)
