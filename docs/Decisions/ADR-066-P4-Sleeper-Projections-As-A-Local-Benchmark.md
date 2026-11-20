---
title: "ADR-066: Sleeper's past projections are a local benchmark only"
date: 2026-11-17
tags: [adr, model, benchmark, data-source, p4]
status: accepted
---
# ADR-066: Sleeper's past projections are a local benchmark only

## Context
[ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) asks for an outside benchmark: does the app beat a projection users already see? Sleeper's own app reads past weekly projections from `api.sleeper.app/projections/nfl/{season}/{week}` (no key). P4 step 7 found it answers for every season back to 2018, with points in half, full and standard PPR and the stats behind them. The numbers are Rotowire's (Sleeper's supplier), and the endpoint is not in Sleeper's documented API. Checked for after-the-fact edits: every week was last modified by the same Tuesday batch, and players hurt during a game keep normal pre-game projections (2024: 8.6 against an actual 2.9), so they are fair to compare against.

## Options considered

**The same example through each option:** Puka Nacua, 2023 week 11, scored 15.5 half PPR; the ML model projected 10.65 and Sleeper 12.45.

| | A: not used | **B: local benchmark** | C: stored and shown in the app |
|---|---|---|---|
| Puka's 12.45 | never fetched | fetched into a git-ignored cache; reports show only totals | stored in PostgreSQL; the Accuracy page shows ours against Sleeper's |
| Outside benchmark | none | every evaluation report | reports and the app |
| Risk | none | low: an undocumented endpoint may change; licensed numbers never enter the public repo | another company's licensed numbers shown to users; an undocumented endpoint becomes a feature |
| Work | none | a fetch script and a report section | a table, a job, API and screens |

## Decision
**Option B** (owner, 2026-11-17).
- `app/model/benchmark.py` fetches (one request per season, week and position, a second apart) and joins through `players.sleeper_id`; `python -m app.scripts.fetch_sleeper_benchmark` fills `api/benchmarks/sleeper/` (git-ignored).
- `python -m app.scripts.evaluate_ml` adds an "Outside benchmark" section when the cache exists: average miss and rank accuracy of 1.0.0, the ML model and Sleeper on the same startable player-games.
- **Never a model input**, never in the database, never committed; tests use synthetic responses.

## Why
An honest "are we better than what users already have?" line in every report, with no licensing exposure and nothing in the app that can break.

## Trade-offs accepted
If Sleeper changes or closes the endpoint, the benchmark stops updating (cached seasons stay usable). Showing the comparison in the app (option C) would need an approved, documented source first.

Related: [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [ADR-002](ADR-002-Fresh-Build.md) · [ML Evaluation Report](../Build-Plan/ML-Evaluation-Report.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md)
