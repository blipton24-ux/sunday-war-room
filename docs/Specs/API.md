---
title: "API (initial /api/v1 endpoints)"
date: 2026-11-08
tags: [spec, api]
---
# API — initial `/api/v1` endpoints (P1)

REST + OpenAPI ([ADR-014](../Decisions/ADR-014-API-REST-OpenAPI.md)). Every endpoint except `/health` requires a valid token. Every league-scoped endpoint checks membership and returns **404** if the user doesn't belong ([Multi-Tenancy](../Concepts/Multi-Tenancy.md)).

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness (no auth) |
| GET | `/api/v1/me` | Current user + memberships |
| DELETE | `/api/v1/me` | Delete account and its data |
| POST | `/api/v1/platforms/sleeper/connect` | `{username}` → 202 + `{job_id}`; the worker finds the user's leagues for the season (result on the job) |
| GET | `/api/v1/leagues` | Leagues the user follows |
| POST | `/api/v1/leagues` | Follow a league `{platform, external_id}` → 202, enqueues `sync_league`. Only leagues returned by the user's latest connect can be followed |
| GET | `/api/v1/leagues/{id}/teams` | Teams in the league (for choosing "my team") |
| PATCH | `/api/v1/leagues/{id}` | Set `my_team_id` |
| DELETE | `/api/v1/leagues/{id}` | Unfollow |
| POST | `/api/v1/leagues/{id}/refresh` | Enqueue sync → returns `{job_id}` (202 Accepted) |
| GET | `/api/v1/jobs/{job_id}` | Job status (queued/running/done/failed) + small `result`; visible to the requester and members of the job's league |
| GET | `/api/v1/leagues/{id}/matchup?week=` | Head-to-head: both lineups, projections, ranges, win probability, scores |
| GET | `/api/v1/leagues/{id}/lineup?week=` | My lineup: current vs optimal, swap suggestions |
| GET | `/api/v1/players/{id}/projection?league_id=&week=` | One projection with factors and range |
| GET | `/api/v1/leagues/{id}/accuracy` | Graded past weeks (genuine predictions only) |

## Conventions
- JSON, snake_case on the wire; the generated TS client exposes the same names.
- Errors: `{ "detail": "...", "code": "..." }` with proper HTTP status codes.
- Long work never happens in a request: it's **202 + job id**.
- Data responses include `as_of` (last sync time) so the UI can show freshness.
- Rate limiting per user on refresh endpoints (and the P3 chat): one manual refresh per league per minute; a refresh while a sync is already queued returns that job instead of starting another.

Related: [REST vs GraphQL](../Concepts/REST-vs-GraphQL.md) · [Data Model](Data-Model.md) · [UI Screens](UI-Screens.md)
