---
title: "ADR-063: Depth charts and player background get their own tables"
date: 2026-11-14
tags: [adr, model, machine-learning, data, database, p4]
status: accepted
---
# ADR-063: Depth charts and player background get their own tables

## Context
The machine-learning model ([ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md)) reads a player's depth-chart tier each week and his background (age, years in the league, draft round and pick). Until P4 these were loaded from nflverse only inside the backtest, so the live weekly compute could not read them (backlog M-22). Step 3 of the [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) stores them in PostgreSQL ([ADR-030](ADR-030-Stats-In-PostgreSQL.md)) for seasons from 2016 ([ADR-062](ADR-062-P4-Training-History-From-2016.md)).

## Options considered

**The same example through each option:** Puka Nacua, Week 11 of 2023.

| | **A: two new tables** | B: columns on existing tables |
|---|---|---|
| Shape | `depth_chart_weeks` (one row per player-week: tier) and `player_background` (one row per player: birth date, rookie season, draft year, round, pick) | `depth_tier` on `player_week_stats`; background on `players` |
| A player on the chart who did not play that week | **Kept** (a useful signal) | Lost: `player_week_stats` has rows only for players who recorded stats |
| Players from 2016 who have retired | **Kept**: every player nflverse knows | Lost: `players` holds the app's current player list only |
| Daily refresh | Each table replaced on its own | The stats reload must keep the depth column in step |

## Decision
**Option A.** `depth_chart_weeks` is filled from nflverse depth charts with the existing tier rules (weekly charts up to 2024; from 2025, the last dated snapshot before each week's first game day, so nothing from game day or later is read). `player_background` is filled from nflverse's player table (`load_players`), replaced whole on each ingest; an empty download never clears it. Empty draft columns mean undrafted.

## Why
Option B loses exactly the cases the model learns from: players who were on the chart but did not play, and players who are no longer in the app's player list.

## Trade-offs accepted
Two more tables to load and keep in step with the stats, and a join when the feature table is built (step 4). `players` keeps today's live status from the platforms; `player_background` holds what never changes.

Related: [ADR-030](ADR-030-Stats-In-PostgreSQL.md) · [ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md) · [ADR-062](ADR-062-P4-Training-History-From-2016.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md)
