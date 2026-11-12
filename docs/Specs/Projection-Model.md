---
title: "Projection Model (v1 spec)"
date: 2026-11-08
tags: [spec, model, data-science]
---
# Projection Model — v1

Own model from nflverse data ([ADR-008](../Decisions/ADR-008-Own-Projection-Model.md)), a cleaner rebuild of the old project's lessons. Approved reuses (method only, rewritten, numbers refit): range method and grading definitions ([ADR-031](../Decisions/ADR-031-Approved-Reuses.md)).

## Inputs
- nflverse weekly player stats, schedules, depth charts, snap counts, player id crosswalk (via `nflreadpy`, through one source module with **schema contracts**).
- Sleeper: rosters, injury status, league scoring rules.

## Output per player-week (per scoring setup)
`points` (median-ish point estimate), **range** `p10 / p50 / p90`, **factors** list, `model_version`, `computed_at`.

## v1 method (simple, explainable)
1. **Score history with the league's own rules.** Compute fantasy points from raw stat columns using each league's scoring settings; never trust a generic "PPR points" column. Unsupported rules are reported, not silently dropped.
2. **Baseline:** weighted recent average of the player's games (recent weeks weigh more), blended with last season's per-game mean early in the season.
3. **Opponent factor:** how much this week's opponent allows to the position vs league average, clamped (e.g. ±25%) and **faded toward 1.0 early in the season** (last season's defensive ratings barely predict this season's).
4. **Role/depth adjustment:** depth-chart rank and recent snap share.
5. **Injury discount:** OUT/IR → 0; Doubtful/Questionable → discounted.
6. **Range:** turn the point estimate into a distribution from backtested errors (empirical residual quantiles by position, **per-position floors**, not a normal curve clipped at zero).

Each step adds a `factor` entry: `{name, value, effect, note}`, shown in Player detail.

## Lineup and matchup
- **Optimal lineup:** fill slots to maximize projected points respecting eligibility (FLEX etc.). Swap suggestions pair each incoming starter with the specific player whose slot it takes.
- **Win probability:** simulate both lineups jointly (~10k draws) from each player's range (v1: independent draws; correlations such as QB↔own receivers are a later upgrade).

## Integrity rules (non-negotiable)
- **Frozen at kickoff:** a projection is never overwritten once that player's game starts.
- **Genuine-only grading:** accuracy counts only projections computed before kickoff.
- **`model_version`** on every row, bumped in the same commit as any math change. Never compare or subtract projections from different versions.
- **Two seasons in play:** the season stats come from vs the season being played are named separately and never assumed equal.
- **Fail loudly** if an nflverse file or column disappears; never silently fall back to an older season.

## Evaluation
Backtest on past seasons (walk-forward: only data available before each week). Metrics: MAE by position, range coverage (80% interval should contain ~80%). A model change ships only if it beats the current one on held-out weeks without making any position notably worse.

## v1 as built (1.0.0)
Constants live in `api/app/model/projection.py`; fitted ranges in `api/app/model/calibration.json`. Results: [Backtest Report](../Build-Plan/Backtest-Report.md).
- Baseline: recent-weighted mean (half-life 4 games) blended with last season's mean, which counts like 3 games. Players with no history start at the 30th percentile of their position.
- Opponent: clamp ±25%, weight n/(n+4) by games the opponent has played. Role: snap share last 2 games vs season, clamp ±15% (RB/WR/TE, 3+ games).
- Injury: Out/IR/PUP/Suspended → 0, Doubtful ×0.25, Questionable ×0.92. Backup QB on the depth chart ×0.25. Injury and depth are live-only (no history), so the backtest doesn't measure them.
- Ranges are fit in Sleeper default half-PPR and applied to every league's scoring (a v1 simplification).
- Lineup: exact assignment (Hungarian algorithm), so overlapping flex slots are handled. Win probability: 10,000 seeded draws from a split normal through p10/p50/p90.

## Ideas under test (P4)
Each idea is a switch in `api/app/model/config.py` (`ModelConfig`); live code runs `SHIPPED`, which changes only in the commit that bumps `MODEL_VERSION`. An idea is kept by the rule in [ADR-055](../Decisions/ADR-055-P4-Keep-Rule.md) after testing on past seasons ([ADR-054](../Decisions/ADR-054-P4-Test-Every-Idea-One-At-A-Time.md)); results are in the [experiment ledger](../Build-Plan/Model-Experiments.md). `python -m app.scripts.backtest --compare shipped,<idea>` runs the comparison. Games spoiled by an injury are left out of the numbers (`app/model/features/injury_games.py`).

## Later upgrades (P2+)
Decided to come after the P1 deploy, with the comparison that motivated them: [ADR-034](../Decisions/ADR-034-Ship-Model-v1-Upgrade-Later.md).

Per-position models on expected points/opportunity, player-level correlations in simulation, rookie priors, weekly auto-refit with a promotion gate, news as a measured factor.

## Rest of season (P2)
Waivers and trades need a season-long number. `app/model/rest_of_season.py` runs the weekly model for every remaining week of the league's fantasy season, using only what is known now, each week's real opponent, byes as 0, short injuries (Out, Doubtful, Questionable) for the next game only and injured reserve for four weeks. Fantasy playoff weeks count 1.5x (owner decision); far-off weeks are not faded. Stored per scoring rules and season shape in `ros_projections`; measured in the [Backtest Report](../Build-Plan/Backtest-Report.md). Smarter long-range projections are P4 ([ADR-049](../Decisions/ADR-049-Phases-Reordered-ESPN-First.md)).

Related: [Lessons from Old Projects](../Lessons-from-Old-Projects.md) · [Data Model](Data-Model.md) · [Testing Levels](../Concepts/Testing-Levels.md)
