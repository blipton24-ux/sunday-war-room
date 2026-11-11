---
title: "Data Model"
date: 2026-11-08
tags: [spec, database]
---
# Data Model (P1, initial)

PostgreSQL via SQLAlchemy, with schema changes only through Alembic ([ADR-015](../Decisions/ADR-015-Database-PostgreSQL.md)). Field lists are a starting point for the build, not final.

## Accounts (Better Auth-managed + ours, [ADR-035](../Decisions/ADR-035-Auth-Better-Auth.md))
| Table | Key fields | Notes |
|---|---|---|
| `users` | id, email, name, image, `plan` (default `free`), created_at | `plan` leaves room for a paid tier ([ADR-011](../Decisions/ADR-011-Monetization.md)) |
| `accounts`, `sessions`, `verifications` | Better Auth's shape, snake_case (`npm run auth:schema` in web/) | Google sign-in links, browser sessions, magic-link tokens; `users.id` stays an integer |

## Platform connections (per user)
| Table | Key fields | Notes |
|---|---|---|
| `platform_accounts` | id, user_id → users, platform (`sleeper`/`espn`/`yahoo`), external_user_id, display_name, credentials_encrypted (P3) | Sleeper needs only a username/id |
| `league_memberships` | id, user_id, league_id → leagues, my_team_id → teams | Which leagues a user follows, and which team is theirs. **The tenant boundary.** |

## Leagues (shared: one row per real platform league)
| Table | Key fields | Notes |
|---|---|---|
| `leagues` | id, platform, external_id, season, name, scoring_rules (JSONB), roster_slots (JSONB), current_week, last_synced_at, **waiver_rules** (JSONB), **season_rules** (JSONB) | Unique (platform, external_id, season). The rules are the league's waiver type, budget, claim window, playoffs and trade deadline ([ADR-046](../Decisions/ADR-046-Any-League-Settings.md)) |
| `teams` | id, league_id, external_id, name, owner_name, avatar_url, waiver_position, waiver_budget_used | |
| `league_transactions` | id, league_id, external_id, kind, status, week, created_at, adds (JSONB), drops (JSONB), waiver_bid | P2: who was dropped when, so waivers can say who is still on waivers. This and last week, refreshed on every sync |
| `roster_entries` | id, team_id, week, player_id, slot (QB/RB/FLEX/BN/IR…), is_starter | Weekly snapshot |
| `matchups` | id, league_id, week, home_team_id, away_team_id, home_score, away_score | Scores as of last sync |

## NFL data (shared by everyone)
| Table | Key fields | Notes |
|---|---|---|
| `players` | id, gsis_id, sleeper_id, espn_id, yahoo_id, name, position, nfl_team, status, injury_status | Crosswalk of platform ids |
| `nfl_games` | id, season, week, home, away, kickoff_at, status | Kickoff drives the freeze rule |
| `player_week_stats` | player_id, season, week, stat columns… | Bulk-loaded from nflverse, idempotent per week ([ADR-030](../Decisions/ADR-030-Stats-In-PostgreSQL.md)) |

## Projections
| Table | Key fields | Notes |
|---|---|---|
| `projections` | id, player_id, season, week, **scoring_key**, points, p10, p50, p90, factors (JSONB), **model_version**, computed_at, **frozen** | `scoring_key` = hash of scoring rules, so leagues with identical scoring share rows. Never overwritten after the player's kickoff. |
| `projection_grades` | projection_id, actual_points, genuine (computed_at < kickoff_at) | Feeds the accuracy page |

## Operations
| Table | Key fields | Notes |
|---|---|---|
| `sync_runs` | id, kind, league_id?, status, started_at, finished_at, error | Shown as "updated N min ago"; debugging |

## Later phases
P3 encrypted ESPN cookies / Yahoo OAuth tokens on `platform_accounts` · P5 `chat_conversations`, `chat_messages`, `news_articles`, `news_chunks` (embedding `vector`), `ai_usage` (daily counts) · P7 `push_subscriptions`, `alerts` ([ADR-049](../Decisions/ADR-049-Phases-Reordered-ESPN-First.md)).

Related: [Multi-Tenancy](../Concepts/Multi-Tenancy.md) · [Architecture](Architecture.md) · [Projection Model](Projection-Model.md)
