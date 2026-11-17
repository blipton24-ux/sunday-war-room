---
title: "Projection Model (v1 spec)"
date: 2026-11-08
tags: [spec, model, data-science]
---
# Projection Model — v1

Own model from nflverse data ([ADR-008](../Decisions/ADR-008-Own-Projection-Model.md)), a cleaner rebuild of the old project's lessons. Approved reuses (method only, rewritten, numbers refit): range method and grading definitions ([ADR-031](../Decisions/ADR-031-Approved-Reuses.md)).

## Inputs
- nflverse weekly player stats, schedules with betting lines (spread and total), weekly injury reports and reserve lists, depth charts, snap counts, player id crosswalk (via `nflreadpy`, through one source module with **schema contracts**); draft picks from P4.
- Sleeper and ESPN: rosters, injury status, league scoring rules.

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
Backtest on past seasons (walk-forward: only data available before each week); explained in [Backtesting and measuring](../Concepts/Backtesting-and-Measuring.md). Metrics: MAE by position, range coverage (80% interval should contain ~80%). A model change ships only by the rule in [ADR-061](../Decisions/ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md): better beyond chance on startable players over four walk-forward test seasons (2022-2025), better in at least three of them, no position worse by more than 0.05, and not worse on the current season's weeks. Rank accuracy and range coverage are reported beside it.

## v1 as built (1.0.0)
Constants live in `api/app/model/projection.py`; fitted ranges in `api/app/model/calibration.json`. Results: [Backtest Report](../Build-Plan/Backtest-Report.md).
- Baseline: recent-weighted mean (half-life 4 games) blended with last season's mean, which counts like 3 games. Players with no history start at the 30th percentile of their position.
- Opponent: clamp ±25%, weight n/(n+4) by games the opponent has played. Role: snap share last 2 games vs season, clamp ±15% (RB/WR/TE, 3+ games).
- Injury: Out/IR/PUP/Suspended → 0, Doubtful ×0.25, Questionable ×0.92. Backup QB on the depth chart ×0.25. Injury and depth are live-only (no history), so the backtest doesn't measure them.
- Ranges are fit in Sleeper default half-PPR and applied to every league's scoring (a v1 simplification).
- Lineup: exact assignment (Hungarian algorithm), so overlapping flex slots are handled. Win probability: 10,000 seeded draws from a split normal through p10/p50/p90.

## 1.1.0: running backs (2026-11-13, removed 2026-11-14)
The first P4 approach shipped tuned settings for running backs only (touchdown luck 50%, betting market 30%, tighter opponent and role limits, first game back -20%, a light carry-volume factor). That approach was replaced on 2026-11-14 ([ADR-060](../Decisions/ADR-060-P4-Machine-Learning-Stats-Then-Score.md)); step 2 of the [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) returned the live model to the 1.0.0 method until 2.0.0 ships (the backtest reproduces 1.0.0's numbers exactly). Its result is kept as a benchmark: held-out 2025, all running backs MAE 4.07 (1.0.0: 4.12; season average 4.08); startable running backs, weeks 5+: -0.172 on 2025 and -0.190 on the 2026 weeks 1-9. Week 10's frozen 1.1.0 rows stay visible on the screens.

## 2.0.0: machine-learning model (planned, P4)
Decided in [ADR-060](../Decisions/ADR-060-P4-Machine-Learning-Stats-Then-Score.md), tested and shipped by [ADR-061](../Decisions/ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md), built per the [P4 Build Plan](../Build-Plan/P4-Build-Plan.md). Explainer: [Machine learning and XGBoost](../Concepts/Machine-Learning-and-XGBoost.md).
1. **Feature table:** one row per player-week, every value known before kickoff: role (target, carry and snap share), efficiency so far, background (age, draft capital), team volume, betting market, opponent allowed by position, availability and depth, game conditions. One function serves the backtest and the live compute.
2. **Stats, then score:** per position, XGBoost predicts volume (targets, carries, pass attempts; count mode) and efficiency per opportunity (catch rate, yards per catch or carry, touchdowns per opportunity, completion rate, yards and interceptions per attempt). Volume × efficiency gives expected stats, scored with each league's own rules; step rules (ESPN "per full 10 yards") and bonuses score their expected value under a learned spread ([ADR-064](../Decisions/ADR-064-P4-Spread-Aware-Scoring-Of-Predicted-Stats.md)).
3. **Training:** only on games before the week projected; retrained weekly; model settings chosen on training seasons only.
4. **Availability:** Out, IR, PUP and Suspended → 0; backup QB discounted; own injury status is a feature.
5. **Ranges:** the residual-quantile method refit on the new model's misses, per position and scoring family.
6. **Factors:** XGBoost's per-signal contributions grouped into plain categories and converted to points.
7. **K and DEF** keep the 1.0.0 method in 2.0.0; their own models follow as 2.1.0.

## Rest of season (P2)
Waivers and trades need a season-long number. `app/model/rest_of_season.py` runs the weekly model for every remaining week of the league's fantasy season, using only what is known now, each week's real opponent, byes as 0, short injuries (Out, Doubtful, Questionable) for the next game only and injured reserve for four weeks. Fantasy playoff weeks count 1.5x (owner decision); far-off weeks are not faded. Stored per scoring rules and season shape in `ros_projections`; measured in the [Backtest Report](../Build-Plan/Backtest-Report.md). Smarter long-range projections are out of P4 (backlog M-15, [ADR-060](../Decisions/ADR-060-P4-Machine-Learning-Stats-Then-Score.md)).

Related: [Lessons from Old Projects](../Lessons-from-Old-Projects.md) · [Data Model](Data-Model.md) · [Testing Levels](../Concepts/Testing-Levels.md)
