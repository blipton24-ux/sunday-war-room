---
title: "Data Model"
date: 2026-11-08
tags: [spec, database]
---
# Data Model

PostgreSQL via SQLAlchemy, with schema changes only through Alembic ([ADR-015](../Decisions/ADR-015-Database-PostgreSQL.md)). Field lists are a starting point for the build, not final.

## Accounts (Better Auth-managed + ours, [ADR-035](../Decisions/ADR-035-Auth-Better-Auth.md))
| Table | Key fields | Notes |
|---|---|---|
| `users` | id, email, name, image, `plan` (default `free`), created_at | `plan` leaves room for a paid tier ([ADR-011](../Decisions/ADR-011-Monetization.md)) |
| `accounts`, `sessions`, `verifications` | Better Auth's shape, snake_case (`npm run auth:schema` in web/) | Google sign-in links, browser sessions, magic-link tokens; `users.id` stays an integer |

## Platform connections (per user)
| Table | Key fields | Notes |
|---|---|---|
| `platform_accounts` | id, user_id → users, platform (`sleeper`/`espn`/`yahoo`), external_user_id, display_name, credentials_encrypted, status (`ok` / `pending` / `needs_reconnect`), credentials_checked_at | Sleeper needs only a username/id. ESPN cookies are stored Fernet-encrypted ([ADR-052](../Decisions/ADR-052-Credential-Encryption.md)); never returned, logged or queued |
| `league_memberships` | id, user_id, league_id → leagues, my_team_id → teams, platform_account_id → platform_accounts | Which leagues a user follows, and which team is theirs. **The tenant boundary.** `platform_account_id`: whose login reads a private league for this user (their own, never a league-mate's) |

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
| `nfl_games` | id, game_id, season, week, game_type, home, away, kickoff_at, home_score, away_score, spread_line, total_line | Kickoff drives the freeze rule; betting lines refreshed by the daily nflverse ingest |
| `live_games` | espn_id, season, week, state, period, clock, scores, possession, remaining_fraction | Game-day state from the ESPN scoreboard (P2) |
| `player_week_stats` | player_id, season, week, stat columns… | Bulk-loaded from nflverse, idempotent per week ([ADR-030](../Decisions/ADR-030-Stats-In-PostgreSQL.md)) |
| `injury_reports` | gsis_id, season, week, report_status, roster_status, practice_status, injury | nflverse weekly injury reports and reserve lists; used for injury-game marking and model features |
| `player_status_snapshots` | player_id, season, week, captured_at, injury_status, depth_chart_order | A row whenever a player's injury status or depth slot changed at a compute, so the model can learn from what was known then |
| P4 (planned) | depth charts, draft picks, trained model files | Stored so the live compute reads the same facts the backtest trained on ([P4 Build Plan](../Build-Plan/P4-Build-Plan.md) steps 2 and 9; where model files live is still to decide) |

## Projections
| Table | Key fields | Notes |
|---|---|---|
| `projections` | id, player_id, season, week, **scoring_key**, points, p10, p50, p90, factors (JSONB), **model_version**, computed_at, **frozen** | `scoring_key` = hash of scoring rules, so leagues with identical scoring share rows. Never overwritten after the player's kickoff. |
| `ros_projections` | player_id, season, from_week, scoring_key, horizon_key, points, games, weekly, model_version | Rest-of-season value for waivers and trades (P2) |
| `projection_grades` | projection_id, actual_points, genuine (computed_at < kickoff_at) | Feeds the accuracy page |

## League activity
| Table | Key fields | Notes |
|---|---|---|
| `matchups` | league_id, week, home/away team, scores, per-player points | Synced from the platform |
| `league_transactions` | league_id, external_id, kind, status, week, adds, drops, waiver_bid | Feeds waiver and trade context (P2) |

## Operations
| Table | Key fields | Notes |
|---|---|---|
| `sync_runs` | id, kind, league_id?, status, started_at, finished_at, error | Shown as "updated N min ago"; debugging |

## Later phases
P3 (built) encrypted ESPN cookies on `platform_accounts` (P7: Yahoo OAuth tokens) · P5 `chat_conversations`, `chat_messages`, `news_articles`, `news_chunks` (embedding `vector`), `ai_usage` (daily counts) · P8 `push_subscriptions`, `alerts` ([ADR-050](../Decisions/ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md)).

Related: [Multi-Tenancy](../Concepts/Multi-Tenancy.md) · [Architecture](Architecture.md) · [Projection Model](Projection-Model.md)
