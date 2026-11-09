---
title: "ADR-030: Historical NFL stats live in PostgreSQL"
date: 2026-11-08
tags: [adr, data, database]
status: accepted
---
# ADR-030: Historical NFL stats live in PostgreSQL (bulk-loaded)

## Context
The projection model needs several seasons of weekly player stats: 100,000+ rows × ~80 columns, immutable once a week is final. nflverse publishes them as Parquet files. The question is whether to copy them into PostgreSQL or keep them as files. Containers on the chosen host ([ADR-022](ADR-022-Hosting-Container-Platform.md)) have disks that are wiped on redeploy and aren't shared between services.

## Options considered
```
① Tuesday: worker recomputes all projections
A Postgres:  SELECT last 3 seasons → pandas → model → save projections
B Parquet:   disk wiped by last deploy → re-download from nflverse → pandas → model
C Hybrid:    download files from cloud storage → pandas → model → save projections

② Player detail shows "last 4 games"
A Postgres:  API runs one SQL query
B Parquet:   API has no files (only the worker does) → needs a copy or pre-saved summary
C Hybrid:    API reads a pre-saved summary from Postgres
```
| | **A: Postgres** | B: Parquet on disk | C: Hybrid |
|---|---|---|---|
| Works on container hosting as-is | ✅ | ❌ needs volume/storage | ✅ needs cloud storage |
| One source of truth | ✅ | ⚠️ copies per worker | ⚠️ two places |
| API can query stats | ✅ | ❌ | ⚠️ summaries only |
| Model load speed | Fast | Fastest | Fast |
| Extra services | None | Volume/storage | Storage |

## Decision
**A.** The `ingest_nflverse` job ([Job Queues](../Concepts/Job-Queues-and-Redis.md)) loads nflverse data into PostgreSQL tables (`player_week_stats`, plus schedules, snap counts and depth charts as needed) with **bulk loading** (`COPY` or batched upserts), never row-by-row inserts. The model reads them into pandas with set-based SQL queries. Loads are **idempotent**: re-running a week replaces that week's rows.

## Why
The old project's database version was slow because it inserted rows one query at a time, not because of the database itself. Bulk loading removes that cost, and Postgres keeps one queryable source of truth that survives redeploys.

## Trade-offs accepted
Slightly slower model loads than reading Parquet locally (seconds, not milliseconds), plus a modest amount of database storage. nflverse schema contracts ([Projection Model](../Specs/Projection-Model.md)) still apply at load time.

Related: [ADR-015 PostgreSQL](ADR-015-Database-PostgreSQL.md) · [ADR-016 Ingestion](ADR-016-Ingestion-Job-Queue.md) · [Data Model](../Specs/Data-Model.md)
