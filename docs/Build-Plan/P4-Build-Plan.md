---
title: "P4 Build Plan"
date: 2026-11-14
tags: [build-plan, p4, model, machine-learning]
---
# Phase 4 Build Plan: a machine-learning projection model

Decisions: [ADR-060](../Decisions/ADR-060-P4-Machine-Learning-Stats-Then-Score.md) (predict the stats with XGBoost, then score them) · [ADR-061](../Decisions/ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) (how it is tested and shipped) · [ADR-062](../Decisions/ADR-062-P4-Training-History-From-2016.md) (training history from 2016). Concept explainer: [Machine learning and XGBoost](../Concepts/Machine-Learning-and-XGBoost.md).

## Status
**Restarted 2026-11-14. Steps 1-6 done (2026-11-16); step 7 in progress (four-season verdict done 2026-11-17).** The first P4 approach (hand-set multipliers tuned position by position, ADR-054 to ADR-059) is replaced.
- **Step 1:** P3 merged into `main` with a merge commit (PR #1); `p4-model` rebased onto it; draft PR #3 open, CI green.
- **Step 2:** the first approach's code removed, its measuring tools kept. Live model 1.1.0 is **not** kept during the build (owner, 2026-11-14): until 2.0.0 ships, the app projects with the 1.0.0 method. Checks: the backtest reproduces 1.0.0 exactly (half PPR overall 4.03, every position row identical; full PPR startable weeks 5+ 6.45 against the season average's 6.50); `--compare shipped,shipped` 0.000; 450 backend tests pass; strict mypy on `app` clean. The four `features/` files keep only their signal code until step 4 moves it into the feature table (owner, 2026-11-14).
- **Step 3:** every season from 2016 loaded (default `nflverse_first_season` 2016); air yards added to the stored stats; two new tables, `depth_chart_weeks` and `player_background` ([ADR-063](../Decisions/ADR-063-P4-Depth-Charts-And-Player-Background-Tables.md)), filled by the ingest. Full load 2016-2026 in about a minute: 70,717 player-games, 2,911 games, 104,811 injury-report rows, 93,048 depth-chart rows, 24,869 players. Checked per season: 32 teams (no old codes), snap share and air yards about 99%, a betting line on every played game, a birth date for every player since 2016, depth tier 1 meaning the same in both nflverse formats (one QB, RB and TE and about three WRs per team-week). Found and fixed on the way: nflverse's 2025+ injury files dropped `date_modified`, so loading the current season alone (the daily refresh) failed; 2016-2020 injury files store season and week as decimals. Left untested on purpose: `load_game_context` and `load_draft_capital`, used only by the old `features/context.py` that step 4 replaces.
- **Step 4:** `api/app/model/ml/features.py` (`build_features(data, targets)`) and `ml/data.py` (`load_model_data`): 116 columns in the groups below, built for all 56,554 skill-position player-games of 2016-2025 in about two seconds. Running totals come from a player's, team's or defense's latest game strictly before the projected week; this week's line, roof, home or away, rest, injury report and depth chart are matched to the week itself. "Higher-ranked teammate out" is built as `out_teammate_share`: the season share of team opportunities held by same-position teammates listed Out or Doubtful or on a reserve list that week. `nfl_games` gained `roof` (for the dome column); rest days come from stored kickoffs. Leak test: every outcome from the projected week on, and every pre-game fact after it, scrambled, and no row moves; it fails when the code is made to read the week's own game, and it also passes on the real data (2023 week 11, 2025 week 1, 2026 week 9). A database test found and fixed a join that broke when no reserve-list rows exist yet. The four old `features/` files and the two loaders only they used are deleted (`injury_games.py` stays).
- **Step 5:** `xgboost-cpu` 3.4.1 added (the CPU-only build: no GPU libraries in the image; strict mypy passes on its type hints). `api/app/model/ml/targets.py` lists the 27 targets (8 QB, 7 RB, 6 WR, 6 TE) and their labels; `ml/train.py` picks settings from 12 candidates on the last training season with early stopping, retrains on every training season, and saves each model as XGBoost JSON with `models.json` (seasons, settings, columns). Repeatable (fixed seed), and a test records that tuning only ever sees the training seasons. `python -m app.scripts.train_ml` writes the [ML Training Report](ML-Training-Report.md) (5.8 minutes for 2022-2025): volume and yardage targets beat each player's own average in all four seasons (QB attempts -13.5%, RB carries -6.7%, WR and TE targets -5.3%, yards per catch -10 to -12%); touchdown rates only tie it, QB rush TD rate and WR carries are slightly worse (backlog M-27); many settings sit at the edge of the grid (M-26). The feature table gained `yards_per_catch` (117 columns).
- **Step 6:** `api/app/model/ml/project.py`: volume x rate gives expected stats; fumbles, first downs, two-point conversions and QB sacks come from league-average rates per opportunity (per position, training seasons); each stat's spread (`variance = a x expected^b`) is fit out of sample on the held-back season; `scoring.score(..., variance)` scores step and bonus rules at their expected value ([ADR-064](../Decisions/ADR-064-P4-Spread-Aware-Scoring-Of-Predicted-Stats.md), owner's choice B); Out, IR, PUP and Suspended score 0, Doubtful 0.25, Questionable 0.92, backup QB 0.25 (the 1.0.0 rules). First preview in points (one season, no bootstrap yet; trained on 2016-2024, graded on 2025, same 6,037 player-games as 1.0.0): full PPR all players 4.26 against 1.0.0's 4.38; **startable weeks 5+ 6.17 against 6.36** (season average 6.47); by position QB 6.42 / 6.51, RB 6.10 / 6.42, WR 6.32 / 6.35, TE 5.71 / 6.11; half PPR startable 5.72 against 5.92. Better than 1.0.0 in every slice and position; step 7 gives the verdict.
- **Step 7 (in progress):** `ml/walk_forward.py` grades the model season by season on 2022-2025, each trained on 2016 to the season before and retrained before weeks 1, 5, 9 and 13 with that season's games so far ([ADR-065](../Decisions/ADR-065-P4-Retrain-Every-Four-Weeks-In-Testing.md), owner's choice B; `train.fit(..., upto=...)`). `compare.ship_evidence` and `compare.ship_rule` apply ADR-061 (pooled better beyond chance, better in 3 of 4 seasons, no position worse by more than 0.05, 2026 not worse); the "2026 not looked at yet" condition is commented out until step 11 (owner, 2026-11-17), so **it must be switched back on for the ship decision**. `python -m app.scripts.evaluate_ml` writes the [ML Evaluation Report](ML-Evaluation-Report.md) (52 minutes; projections cached). **Result: the ship rule passes in half, full and standard PPR.** Half PPR, startable, injury games left out: 5.49 against 1.0.0's 5.73 (season average 5.99), change -0.239 (95% interval -0.297 to -0.185), better beyond chance in each of the four seasons on its own (-0.21, -0.19, -0.29, -0.27) and at every position (QB -0.33, TE -0.29, WR -0.25, RB -0.17); weeks 1-4 -0.41, weeks 5+ -0.19; everything counted -0.24; rank accuracy 0.353 against 0.291. 2025 running backs, every game: 4.00 against 1.0.0's 4.12 and 1.1.0's published 4.07. **Outside benchmark** ([ADR-066](../Decisions/ADR-066-P4-Sleeper-Projections-As-A-Local-Benchmark.md), owner's choice B): Sleeper's past projections (Rotowire's) are fetched into a git-ignored cache (`python -m app.scripts.fetch_sleeper_benchmark`), checked for after-the-fact edits (none), and added to the report: over the four seasons the ML model ties them on average miss (half PPR 5.49 against 5.48; standard 5.05 against 5.07) and beats them at QB, while Sleeper orders players better (0.368 against 0.343, backlog M-28). **Availability fitted (M-29, ADR-068): 5.49 to 5.47, now even with Sleeper (5.476 against 5.477).** Still to do in step 7: the injury news source (M-34), the wider settings grid (M-26), the weak targets (M-27) and the red-zone data question (M-24).

## Why
Every recommendation in the app (start/sit, waivers, trades, win chance) rests on the projection. Model 1.0.0 misses startable players by 6.45 points on average (held-out 2025, full PPR), a plain season average by 6.50, and the earlier project's model by 5.83. The first P4 approach shipped one position (running backs, about 0.17 better) after two rounds of dial-tuning and hit three limits: it only saw points, its multipliers double counted, and it tuned dials one at a time ([ADR-060](../Decisions/ADR-060-P4-Machine-Learning-Stats-Then-Score.md)).

## How the new model works

```
history before the week ─► feature table ─► XGBoost: volume      ─┐
 (stats, snaps, lines,      one row per       (targets, carries,   ├─► expected stats ─► league scoring ─► points
  injuries, depth, ...)     player-week        pass attempts)       │   (volume × rate)    (each league's       + range
                                            ─► XGBoost: efficiency ─┘                       own rules)         + "why" factors
                                               (catch rate, yards per
                                                catch, TDs per touch, ...)
```

**The same example all the way through:** a wide receiver, Week 11, full PPR.
1. **Feature row:** recent target share 24%, season 21%, team's expected pass attempts 36, implied team score 25.5, opponent allows +8% targets to receivers, home, healthy, depth tier 1.
2. **Volume model:** 8.1 targets.
3. **Efficiency models:** 66% caught, 12.4 yards a catch, 0.055 touchdowns per target.
4. **Expected stats:** 5.4 catches, 66 yards, 0.45 touchdowns.
5. **Scored with his league's rules:** 5.4 + 6.6 + 2.7 = **16.3 in full PPR** (13.6 in half PPR). Any custom rule is scored the same way.
6. **Range and factors:** the 80% range comes from the backtest's misses; the "why" list reads "his role +3.1, team volume +1.2, opponent +0.6, betting market +0.4…" in points.

## The feature table (one row per player-week)

Every value is known **before that week's kickoff**. One function builds this table for both the backtest and the live compute, so training and live projections never differ in how a signal is computed.

| Group | Columns (first version) | Source (stored today?) |
|---|---|---|
| Player role | target share, carry share, snap share, air-yards share, recent (last 3) and season, plus trend; pass-attempt share for QBs | nflverse weekly stats, snap counts (yes; air yards backtest-only) |
| Player efficiency so far | catch rate, yards per target, yards per carry, touchdowns per opportunity, completion rate, yards per attempt, interception rate, each recent and season with the number of opportunities behind it | nflverse weekly stats (yes) |
| Player background | age, years in the league, draft round and pick, games played this season and last, last season's per-game volume | rosters, draft picks (draft picks backtest-only) |
| Team | team plays per game, pass rate, points per game, recent and season | derived from weekly stats (yes) |
| Betting market | spread, total, implied team score, implied opponent score | `nfl_games.spread_line`, `total_line` (yes) |
| Opponent | targets, receiving yards, rushing yards and touchdowns allowed to the position (recent and season, adjusted for games played), sack and interception rate | derived from weekly stats (yes) |
| Availability and depth | own injury status (Questionable, Doubtful), first game back from a reserve list, depth-chart tier, a higher-ranked teammate at his position out | `injury_reports`, `player_status_snapshots`, depth charts (depth backtest-only) |
| Game | home or away, dome, rest days, week of season, weeks 1-4 flag | schedules (yes) |

**Left out on purpose:** wind (the free data records it after the game, not as a forecast; backlog M-21), nflverse's own expected fantasy points (fit on many seasons that may include later ones, so it can leak the future), and red-zone / goal-line usage until play-by-play loading is decided (backlog M-24). Missing values (a rookie with no history) are left empty; XGBoost handles empty values natively.

## What each position's models predict

| Position | Volume (count models) | Efficiency (rate models, weighted by opportunities) |
|---|---|---|
| QB | pass attempts, carries | completion rate, yards per attempt, passing TDs per attempt, interceptions per attempt, yards per carry, rushing TDs per carry |
| RB | carries, targets | yards per carry, rushing TDs per carry, catch rate, yards per catch, receiving TDs per target |
| WR, TE | targets, carries | catch rate, yards per catch, receiving TDs per target, yards per carry |
| All | | fumbles lost and two-point conversions from league-average rates per opportunity (too rare to model) |
| K, DEF | step 12 | step 12 |

Volume models use XGBoost's count mode (Poisson); rate models use the ordinary mode with each game weighted by its opportunities, so a 1-target game counts little.

## Steps

### 1. Merge P3 into `main` first (if not merged yet)
`p4-model` was branched from `p3-espn` before P3's pull request (#1) was merged, so it holds every P3 commit plus the P4 work.
- If PR #1 is still open: confirm CI is green, merge it into `main`, then rebase `p4-model` onto the new `main` (or start a fresh `p4-ml` branch from `main` and bring over the P4 commits), so the P4 pull request shows only P4 changes.
- P3's open real-league checks (Verification Gaps V-36..V-42) stay open; they do not block P4.
- **Check:** `git log main..p4-model` lists only P4 commits; CI green on the rebased branch.

### 2. Remove the first approach (keep the tools)
- **Delete:** `api/app/model/config.py` (`ModelConfig`, `SHIPPED`, `CANDIDATES`), the idea branches in `api/app/model/projection.py` (back to the 1.0.0 method), `api/app/scripts/tune.py`, `api/backtest/tuning/`, the `--sweep` and idea paths in `api/app/scripts/backtest.py` (`with_round_2_columns`, `Extras` plumbing), and the tests for them (`test_model_ideas.py`, `test_round_2.py`). (`test_config.py` stays: it tests the app's settings, not `ModelConfig`.)
- **Review `api/app/model/features/`:** code that computes a signal (target and carry share in `opportunity.py`, team carries in `rushing.py`, defense allowed by position in `defense.py`, game context in `context.py`) moves into the feature table in step 4; code that only applied a multiplier is deleted.
- **Keep:** `compare.py`, `metrics.py`, `features/injury_games.py`, `services/versions.py`, the walk-forward backtest core, scoring (`scoring.py`, `scoring_espn.py`), ranges (`distribution.py`), lineup, win probability, the stored betting lines and their daily refresh, `injury_reports`, `player_status_snapshots`.
- **Live model:** `MODEL_VERSION` returns to `"1.0.0"` (the same method as the earlier 1.0.0 rows). Week 10's frozen 1.1.0 rows stay visible through `versions.py`.
- **Check:** the backtest reproduces 1.0.0's numbers (startable 6.45 on 2025, full PPR; half PPR overall 4.03); `--compare shipped,shipped` shows 0.000; pytest, strict mypy and CI green.

### 3. Data for training
More seasons mean better trees. Load raw stats, snap counts, schedules with lines, rosters and reserve lists, injury reports, depth charts and draft picks for **every season from 2016** ([ADR-062](../Decisions/ADR-062-P4-Training-History-From-2016.md); 2021 onward is loaded today, so 2016-2020 are new). Training data stays in PostgreSQL per [ADR-030](../Decisions/ADR-030-Stats-In-PostgreSQL.md); depth charts and player background (birth date, rookie season, draft round and pick) get stored tables so the live compute can read them (backlog M-22, [ADR-063](../Decisions/ADR-063-P4-Depth-Charts-And-Player-Background-Tables.md)). Depth charts changed shape in 2025; the tier mapping handles both.

### 4. The feature table
`api/app/model/ml/features.py`: `build_features(history, season, week) -> DataFrame`, pure, one row per player-week, columns as in the table above. Unit tests per column, plus the **leak test**: change every game at or after the projected week and the row must not move.

### 5. Training
`api/app/model/ml/train.py`: one XGBoost model per position and target. Training for season S uses only games before S (and, live, the earlier weeks of S). Settings (tree depth, learning rate, number of trees, minimum games per leaf, column sampling) are chosen with the last training season held back and early stopping, never on a test season ([ADR-061](../Decisions/ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md)). A signal or setting is kept only if its gain beats that position's bootstrap noise. Models save as XGBoost JSON with the training seasons, settings and feature list beside them. Add `xgboost` (CPU build) with uv for Windows and Linux; check strict mypy against its type hints.

### 6. Stats, then score
`api/app/model/ml/project.py`: volume × rates → expected stats → each league's scoring (the existing scoring code, Sleeper and ESPN maps) → points. The availability rules that hold now stay: Out, IR, PUP and Suspended → 0; backup QB on the depth chart discounted. Questionable and Doubtful players are handled by the injury-status feature (learned from players who played) plus the existing discount for the chance he sits, until that discount is fitted (needs a projected-and-sat test).

### 7. Evaluation upgrades
- `compare.py` and `backtest.py` run the four test seasons (2022-2025) walk-forward and apply the ship rule from ADR-061: pooled gain beyond chance, better in at least 3 of 4 seasons, no position worse by more than 0.05, 2026 not worse.
- New report lines: **rank accuracy** (Spearman per week and position), **range coverage** per position and scoring format, **everything counted** beside the injury-left-out number, weeks 1-4 and 5+ apart, rest-of-season accuracy.
- Benchmarks in every report: season average, 1.0.0, the removed 1.1.0's published numbers.
- **Outside benchmark:** check whether Sleeper's past weekly projections can be fetched for 2024-2026. If so, propose it as a data source (ADR) and add it as a benchmark column (never a model input).
- **Model improvements** ([ADR-067](../Decisions/ADR-067-P4-Scope-For-The-Best-Model-Now.md)), each run through `evaluate_ml` and kept only if it beats noise; the order is cheapest evidence first:
  1. Availability (M-29) and how Questionable players are shown, with injury news (M-34): a side-by-side first. **Availability done (2026-11-18, [ADR-068](../Decisions/ADR-068-P4-Questionable-Players-Projected-If-Playing.md)):** Questionable and Doubtful players are projected as if they play, less a fitted trim, with the fitted chance he plays and the chance-weighted value beside it; half PPR startable 5.489 to 5.472, full 5.967 to 5.946, standard 5.049 to 5.035, lower in every season and position (no paired bootstrap against the earlier ML run: its cache was not kept). The news source (M-34) is still to do; Friday practice status is backlog M-35.
  2. Tuning run: wider settings grid (M-26), plain average for weak targets (M-27), training from 2012 (M-31).
  3. Red-zone and goal-line usage from play-by-play (M-24; data-source ADR first), and the scoring rules it unlocks (M-12, M-17).
  4. New signals (M-33) and the blend with 1.0.0 (M-30); the ordering gap to Sleeper (M-28) is re-measured after each.

### 8. Ranges
Refit the residual-quantile method ([ADR-031](../Decisions/ADR-031-Approved-Reuses.md) reuse 2) on the new model's backtest misses, per position and per scoring family (backlog M-08). XGBoost's percentile mode is tried only if coverage misses 80% by more than a few points.

### 9. Explanations on the Player screen
XGBoost's per-signal contributions (`pred_contribs`) for each stat, grouped into plain categories (his role, team volume, opponent, betting market, injury and depth, history and background), multiplied through the league's scoring into points. The factor shape `{name, value, effect, note}` stays, so the API and screens change little. Check in the browser on a real league.

### 10. Live compute and weekly retraining
- The weekly compute builds the same feature table from stored data before kickoff and loads the current model files.
- **Late injuries (M-10) and injury news (M-34, live part):** a side-by-side on sources and timing (Sunday-morning refresh, rate limits) before building ([ADR-067](../Decisions/ADR-067-P4-Scope-For-The-Best-Model-Now.md)).
- A worker job retrains every Tuesday after the stats ingest, on everything played so far, and replaces the live files only if the retrained model is not worse on the latest weeks (backlog M-14). Each projection row records which training produced it.

### 11. Model 2.0.0: owner review and ship
Full report on the four test seasons, the one look at the 2026 weeks played so far, example projections for players the owner knows, and the owner's ship decision. Before it: the Accuracy page's version switch (U-17), unmatched players (M-13, M-19), and switching the "2026 not looked at yet" condition back on in `compare.ship_rule` ([ADR-067](../Decisions/ADR-067-P4-Scope-For-The-Best-Model-Now.md)). Then, in one commit: `MODEL_VERSION = "2.0.0"`, refit ranges, spec update ([Projection Model](../Specs/Projection-Model.md)), Backtest Report regenerated, CI green.

### 12. Kickers and defenses
K: field-goal attempts by distance band and extra points (volume) from the team's implied score, dome and drive data; made rate by distance. DEF: sacks, interceptions, fumble recoveries, touchdowns and points allowed from the opponent's implied score and the opposing QB's sack and turnover rates (backlog M-04). Same pipeline, same ship rule; ships as 2.1.0 when it passes. Until then K and DEF keep the 1.0.0 method inside 2.0.0.

### 13. Rest-of-season model
A separate long-range model for rest-of-season value on the trade and waiver screens (M-15, [ADR-067](../Decisions/ADR-067-P4-Scope-For-The-Best-Model-Now.md)): trained on each player's remaining-season output from the same feature table, tested walk-forward like the weekly model on the rest-of-season backtest (`backtest.rest_of_season_backtest`). Ships when it beats the current method (the weekly model carried across the schedule) at every position; until then 2.0.0 keeps that method.

## Rough time
About 7 to 8½ working sessions, plus the owner's review time: steps 1-4, steps 5-6, step 7 (two to three sessions with the model improvements, [ADR-067](../Decisions/ADR-067-P4-Scope-For-The-Best-Model-Now.md)), step 8, steps 9-10, steps 11-12, step 13.

## Decided before the build (2026-11-14)
- **Training history from 2016** ([ADR-062](../Decisions/ADR-062-P4-Training-History-From-2016.md)).
- **P3 merged first**, as step 1.
- **1.1.0 not kept live** during the build ([ADR-060](../Decisions/ADR-060-P4-Machine-Learning-Stats-Then-Score.md)).

## Decisions still to make
Each follows [ADR-003](../Decisions/ADR-003-Documentation-Standard.md), before the step that needs it:
- **Where model files live, and what a weekly retrain means for `model_version`** (step 10): for example, files in the database with "2.0.0" as the method and a training date per row.
- ~~Sleeper's past projections as a benchmark source~~: decided, [ADR-066](../Decisions/ADR-066-P4-Sleeper-Projections-As-A-Local-Benchmark.md).
- **Play-by-play for red-zone and goal-line usage** (backlog M-24): about 100 MB a season, for a strong touchdown signal (step 7).
- **How Questionable players are projected and shown, and an injury news source** (M-29, M-34; step 7, live part step 10).
- **Late injuries** (M-10; step 10).

## Verification
- Step 2 reproduces 1.0.0 exactly; `--compare shipped,shipped` is 0.000.
- Every feature column has a unit test, plus the leak test across the whole table.
- Training is repeatable: the same seasons and settings give the same model (fixed seed).
- The ship rule and new report lines are unit-tested on a small hand-made frame with known answers.
- Each version: pytest, strict mypy, web tests, the 2026 one-look check, the Accuracy page still showing earlier weeks, and the Player screen's factors read in the browser on a real league. CI green before each merge.

Out of P4 ([ADR-060](../Decisions/ADR-060-P4-Machine-Learning-Stats-Then-Score.md)): IDP (M-18), keeper and dynasty value, correlated simulation (M-07). Rest of season came back in as step 13 ([ADR-067](../Decisions/ADR-067-P4-Scope-For-The-Best-Model-Now.md)).

Related: [ADR-060](../Decisions/ADR-060-P4-Machine-Learning-Stats-Then-Score.md) · [ADR-061](../Decisions/ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [Projection Model](../Specs/Projection-Model.md) · [Backtest Report](Backtest-Report.md) · [Improvement Backlog](Improvement-Backlog.md) · [Later Phases Outline](P2-P8-Outline.md)
