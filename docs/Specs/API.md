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
| GET | `/api/v1/leagues/{id}/matchup?week=` | Head-to-head: both lineups, projections, ranges, win probability, scores. P2 live: each player's points so far, game clock, has-the-ball, share of the game left; `live`, `clock_source` (scoreboard / kickoff estimate), `scores_updated_at`. 409 `team_not_chosen` until my team is set |
| GET | `/api/v1/leagues/{id}/lineup?week=` | My lineup: current vs optimal, swap suggestions |
| GET | `/api/v1/players/{id}/projection?league_id=&week=` | One projection with factors and range, plus the last 4 games scored with the league's rules. Membership of `league_id` is checked (404) |
| GET | `/api/v1/leagues/{id}/accuracy` | Graded past weeks (genuine predictions only) |
| GET | `/api/v1/leagues/{id}/trades/rosters` | P2: every team's roster with rest-of-season points per week, league kind and trade deadline |
| POST | `/api/v1/leagues/{id}/trades/evaluate` | P2: `{team_a_id, team_b_id, a_gives, b_gives}` → each team's best-lineup points per week before/after, drops needed, lineups ([ADR-048](../Decisions/ADR-048-Trades-Lineup-Impact.md)). 422 `invalid_trade` |
| GET | `/api/v1/leagues/{id}/trades/suggestions?max_loss=` | P2: trades that help my lineup most while the other team loses at most `max_loss` pts/week (0–3). Cached per sync |
| GET | `/api/v1/leagues/{id}/waivers?horizon=ros\|week` | P2: free agents ranked by points added to my best lineup, suggested drop, waiver status, FAAB bid guide ([ADR-047](../Decisions/ADR-047-Waivers-Value-Added.md)). 409 `team_not_chosen` until my team is set |

## Conventions
- JSON, snake_case on the wire; the generated TS client exposes the same names.
- Errors: `{ "detail": "...", "code": "..." }` with proper HTTP status codes.
- Long work never happens in a request: it's **202 + job id**.
- Data responses include `as_of` (last sync time) so the UI can show freshness, and `model_version`.
- Player rows carry `game_status` (upcoming / in_progress / final / bye); players whose game started are locked in lineup suggestions. `actual_points` is filled from nflverse once a game is final.
- Screens list `unsupported_rules`: league scoring rules that aren't scored yet (shown, never hidden).
- Rate limiting per user on refresh endpoints (and the P5 chat): one manual refresh per league per minute; a refresh while a sync is already queued returns that job instead of starting another.

Related: [REST vs GraphQL](../Concepts/REST-vs-GraphQL.md) · [Data Model](Data-Model.md) · [UI Screens](UI-Screens.md)
