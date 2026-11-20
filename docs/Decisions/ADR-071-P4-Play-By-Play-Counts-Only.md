---
title: "ADR-071: Play-by-play is read for per-player-week counts only"
date: 2026-11-20
tags: [adr, model, data-source, nflverse, p4]
status: accepted
---
# ADR-071: Play-by-play is read for per-player-week counts only

## Context
The weekly box score says how many targets and carries a player had, not where on the field. Goal-line carries (inside the 5) and red-zone and end-zone targets are the strongest known touchdown signals, and touchdown rates are the model's weakest targets (backlog M-24, M-27; [ADR-070](ADR-070-P4-Tuning-Run-Grid-Targets-History.md) left them to this signal). Play-by-play also carries what some scoring rules need (touchdown distance, field-goal yardage; M-17) and special-teams fumbles (M-12).

nflverse publishes play-by-play per season through the `nflreadpy` library already used: about 20 MB compressed (checked 2026-11-20: 2016 20.6 MB, 2025 21.6 MB), about 48,000 plays and 370 columns a season.

## Options considered
**The same example:** Puka Nacua, week 11: the box score says 9 targets and 1 touchdown; play-by-play adds 3 red-zone targets and 2 end-zone targets.

| | **A: counts only** | B: every play in the database | C: counts plus raw files on disk |
|---|---|---|---|
| Stored | one small table, per player per week (about 6,000 rows a season) | every play and column (over 500,000 rows) | the small table and about 300 MB of files |
| Database added | a few MB | about 1-2 GB | a few MB |
| A new count later | re-download the seasons (about a minute each) | a query | re-count from disk |
| Deployed (P8) | fits a small database | needs a larger one | files sit badly in a container |

## Decision
**Option A** (owner, 2026-11-20).
- `app/sources/nflverse.py` stays the only module that reads nflverse; a play-by-play loader there turns each season into per-player-week counts and discards the plays.
- The counts are stored in a new table (schema in the step 7d build): goal-line carries, red-zone and end-zone targets, red-zone carries, and the per-week counts the M-12 and M-17 scoring rules need.
- The daily refresh reloads the current season's counts; a full load covers every training season (2016, or 2012 if [ADR-070](ADR-070-P4-Tuning-Run-Grid-Targets-History.md)'s test keeps it).
- The new features use only games before the one projected, checked by the existing leak test, and are kept only if the evaluation improves beyond chance (step 7d).

## Why
Only the counts are needed, and re-downloading a season is cheap, so storing every play buys little while making the database ten times larger for deployment.

## Trade-offs accepted
A count not foreseen now needs a re-download of every season (minutes, not hours). The daily refresh downloads about 20 MB more.

Related: [ADR-070](ADR-070-P4-Tuning-Run-Grid-Targets-History.md) · [ADR-030](ADR-030-Stats-In-PostgreSQL.md) · [ADR-063](ADR-063-P4-Depth-Charts-And-Player-Background-Tables.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md)
