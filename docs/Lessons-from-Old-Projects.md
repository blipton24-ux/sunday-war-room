---
title: "Lessons from Old Projects"
date: 2026-11-08
tags: [lessons, prior-art]
---
# Lessons from Old Projects

Reviewed: `fantasy-football-assistant/` (its `CLAUDE.md` and `backend/app/`: `sleeper_client.py`, `nflverse_client.py`, `scoring/projection.py`, `scoring/fantasy_points.py`, `scoring/scoring_rules.py`, `scoring/start_sit.py`, `accuracy.py`, `news_client.py`, `llm_client.py`) and its fork `fantasy-football-app/` (accounts + multi-league).

Per [ADR-002](Decisions/ADR-002-Fresh-Build.md), these are **lessons, not code**. Anything marked *candidate reuse* needs the owner's explicit OK before it's carried over.

## Keep (ideas proven worth it)
| Lesson                                                                                                | Why it mattered                                                                                                                                                                                       | Sunday War Room home                                                                             |
| ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **One module per external source**                                                                    | Only one place knows each API's URLs/formats; everything downstream sees plain data                                                                                                                   | [Architecture](Specs/Architecture.md), [Adapter Pattern](Concepts/Adapter-Pattern.md) |
| **nflverse renames must fail loudly**                                                                 | `nfl_data_py` hard-coded a retired file path; the app silently projected 2026 from 2024 data, and every number still *looked* plausible. Fix: ordered candidate paths + column "contracts" that raise | `sources/nflverse.py`                                                                 |
| **Two seasons are always in play**                                                                    | Stats season ≠ season being played; conflating them shipped a bug                                                                                                                                     | [Projection Model](Specs/Projection-Model.md)                                         |
| **Freeze projections at kickoff**                                                                     | Refresh used to rewrite past weeks with hindsight (today's injuries, closing lines)                                                                                                                   | Integrity rules                                                                       |
| **Grade only genuine predictions**                                                                    | Rows computed after kickoff were being graded as if they were forecasts                                                                                                                               | Accuracy page                                                                         |
| **`model_version` on every projection**                                                               | Waivers compared a free agent on the old formula (18.15) against rostered players on the new one                                                                                                      | Data model                                                                            |
| **Score with the league's own rules**                                                                 | Generic PPR columns don't match custom leagues; unsupported rules are reported, not dropped                                                                                                           | Model step 1                                                                          |
| **Projection = distribution**                                                                         | Inside a 3-point gap, the lower-projected player wins ~32–44% of the time, so ranges and win probability matter                                                                                       | Model + lineup                                                                        |
| **Per-position floors, not clip-at-zero**                                                             | Clipping broke calibration (D/ST 90% interval covered only 76%)                                                                                                                                       | Range step                                                                            |
| **Opponent ratings fade across seasons**                                                              | Last season's defense vs a position barely predicts this season's                                                                                                                                     | Opponent factor                                                                       |
| **Measure correlations at player level**                                                              | Team-average residuals inflated a same-game correlation about tenfold                                                                                                                                 | P2 simulation                                                                         |
| **Pure scoring modules + visible factors**                                                            | Easy to test, and every number is explainable                                                                                                                                                         | `model/`                                                                              |
| **Lineup swaps pair by slot, not by rank**                                                            | Naive zip paired an incoming TE with an outgoing QB                                                                                                                                                   | Lineup optimizer                                                                      |
| **Ship model changes only if they beat the incumbent** on held-out weeks, with no position regressing | Hid a QB regression otherwise                                                                                                                                                                         | Evaluation                                                                            |
| **News: attribute by athlete id, verify quotes, badge until proven**                                  | Name matching pins facts on the wrong player; LLMs can invent quotes                                                                                                                                  | [ADR-018](Decisions/ADR-018-AI-Agent-With-RAG.md)                                     |
| **Sleeper has injury body-part detail** nflverse lacks (IR players drop off the injury report)        | Torn ACL misread as "unspecified, back Week 8"                                                                                                                                                        | Sleeper adapter                                                                       |
| **Player-id crosswalk must handle duplicates**, not just gaps                                         | Source CSV has duplicate gsis/espn ids                                                                                                                                                                | Adapter/crosswalk                                                                     |
| **Semantic design tokens**                                                                            | Redefining Tailwind's own palette inverted made every edit confusing                                                                                                                                  | [ADR-023](Decisions/ADR-023-Visual-Broadcast-Style.md)                                |
| **Scores polling is separate from projections**                                                       | A scores refresh must never trigger a recompute                                                                                                                                                       | P2 live scores                                                                        |

## Change (where Sunday War Room deliberately differs)
| Old | Sunday War Room | Why |
|---|---|---|
| SQLite file + hand-bumped `SCHEMA_VERSION`, rebuild-the-db resets | PostgreSQL + Alembic migrations | Multi-user, deployed, safe schema changes |
| Desktop window (pywebview), one process | Web/PWA, 5 containers | Public product, usable from any device |
| Threads/subprocesses for background work | Redis queue + ARQ workers | Retries, scaling, observability |
| Email + password (scrypt), session cookie (fork) | Auth.js: Google + magic links | No password storage |
| ESPN as primary platform | Sleeper first | Official public API, no cookies |
| Local LLM (Ollama) for news | Hosted Claude (P3) | Works for all users; the old code already isolated the LLM in one module for exactly this swap |
| No CI, no containers, never deployed | Full CI/CD, Docker, deployed | Production-grade bar ([ADR-004](Decisions/ADR-004-Production-Grade-Bar.md)) |

## Resolved: stats storage
The old project moved historical stats **out** of the database into cached parquet files read by pandas (thousands of row inserts were slow and the data is immutable). Sunday War Room decided on Postgres tables with **bulk loading**, which fixes the actual cause of the old slowness (row-by-row inserts): [ADR-030](Decisions/ADR-030-Stats-In-PostgreSQL.md).

## Reuse decisions
Decided in [ADR-031](Decisions/ADR-031-Approved-Reuses.md):
- Scoring-rule mapping table: **idea now** (Sleeper mapping built fresh with all three rule shapes), **ESPN table adapted in P4**.
- Residual-quantile approach for ranges: **method reused**, all numbers refit on Sunday War Room's own backtest.
- Backtest metric definitions: **reused** (MAE, RMSE, bias, rank correlation, bucket error, interval coverage).

Related: [ADR-002 Fresh build](Decisions/ADR-002-Fresh-Build.md) · [ADR-008 Own model](Decisions/ADR-008-Own-Projection-Model.md) · [Projection Model](Specs/Projection-Model.md)
