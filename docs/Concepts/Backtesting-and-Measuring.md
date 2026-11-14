---
title: "Backtesting and measuring a projection model"
date: 2026-11-14
tags: [concept, model, backtest, machine-learning]
---
# Backtesting and measuring a projection model

**Backtesting** = pretending to live through past seasons week by week, making the projections the model *would* have made with only what was known then, and grading them against what actually happened. It is how we know whether a model is good before users rely on it, and whether a change makes it better or only looks better.

## The one rule: never peek at the future
A projection for Week 11 of 2024 may only use games before Week 11 of 2024, and a model trained to make it may only have learned from earlier games. Breaking this is called **leakage**, and it makes a backtest look better than the live app can ever be. Two guards:
- **Walk-forward:** the backtest steps through the weeks in order, rebuilding everything from scratch each week from the past only.
- **The leak test:** a unit test changes every game at or after the projected week and fails if the projection moves.

## Side by side: grading "start A or B?" for Week 11
```
Week 11, 2024 — what the backtest does
  1. Take every game before Week 11 (and earlier seasons)
  2. Build the feature table, run the model     → A: 14.2   B: 12.8   (projections)
  3. Look up what happened                       → A: 9.0    B: 17.5   (actual points)
  4. Grade:  miss A = |14.2 − 9.0| = 5.2,  miss B = |12.8 − 17.5| = 4.7
             order: projected A > B, actual B > A  → ordering was wrong this week
  5. Repeat for every player, every week, every test season
```

## What gets measured
| Measure | Plain meaning | Why it matters |
|---|---|---|
| **Average miss** (MAE, mean absolute error) | On average, how many points off the projection was | The main yardstick; 6.45 points per startable player for model 1.0.0 on 2025 |
| **Startable slice** | Only players who matter for lineups: each week's top 15 QB and TE, top 36 RB and WR | A deep bench player projected 1.2 who scores 0 makes any model look good |
| **Rank accuracy** (Spearman correlation) | How well the projected order at a position matches the actual order, 1.0 = perfect | Start/sit is about order, not exact points |
| **Range coverage** | How often the actual score lands inside the 80% range; should be about 80% | Win chances and floor/ceiling are only honest if ranges are |
| **Weeks 1-4 apart from 5+** | Early weeks have little current-season data | A model can be good in October and poor in September |
| **Everything counted vs injury games left out** | Games where a player got hurt are left out when judging a model, since no model could know; both numbers are shown | Fair for comparing models; users still live with injury games |

## Is the difference real or luck? (the paired bootstrap)
Two models are always graded on **exactly the same player-games** (paired), so neither gets easier players. Then:
1. Compute the change in average miss, week by week.
2. **Bootstrap:** draw the weeks at random with replacement (some weeks twice, some not at all) and recompute the change, 2,000 times.
3. The middle 95% of those 2,000 results is the **95% interval**. If the whole interval is below zero, the new model is better **beyond chance**; if it crosses zero, the difference is **noise**.

Weeks are drawn whole because players in the same week share weather, upsets and injuries; treating each player as independent would make noise look like a result.

## Held-out seasons
A model tuned on the games it is graded on will always look good. So seasons are kept apart ([ADR-061](../Decisions/ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md)):

| Season | Used to train | Used to choose model settings | Used to grade |
|---|---|---|---|
| Seasons before the one tested | yes | yes (the last one held back) | no |
| The tested season (each of 2022-2025 in turn) | no | no | **yes** |
| 2026 weeks played so far | no | no | **once per version, before it ships** |

A new version ships only if it is better beyond chance over the four test seasons together, better in at least three of them on its own, no position worse by more than 0.05 points, and not worse on 2026.

## Benchmarks: better than what?
- **Plain season average:** the simplest possible projection. A model that can't beat it adds nothing.
- **The live model** (1.0.0 today): what a new version must beat to ship.
- **The earlier project's model** (5.83 on 2025): a bar we know is reachable.
- **Sleeper's own projections** (planned, if past ones can be fetched): what users already see elsewhere.

## Live measuring: the Accuracy page
The backtest measures the past; the Accuracy page measures the real thing. Every projection is **frozen at kickoff** and graded only if it was made before kickoff (**genuine-only grading**), and every row carries the `model_version` that made it, so versions are never mixed.

## Where it lives
`api/app/scripts/backtest.py` (the walk-forward run and the report), `api/app/model/compare.py` (paired comparison, bootstrap, ship rule), `api/app/model/metrics.py` (startable slice), `api/app/model/features/injury_games.py` (injury-game marking). `python -m app.scripts.backtest` writes the [Backtest Report](../Build-Plan/Backtest-Report.md); P4 steps 2 and 7 rework it for the machine-learning model ([P4 Build Plan](../Build-Plan/P4-Build-Plan.md)).

## Words you'll see
- **Held-out / out-of-sample:** games the model never saw while being built.
- **Overfitting:** learning the noise of past games, so the model looks good in training and worse on new games.
- **Calibration:** whether ranges and probabilities mean what they say (80% ranges hold 80% of results).
- **Baseline / benchmark:** what a model is compared against.

Related: [Machine learning and XGBoost](Machine-Learning-and-XGBoost.md) · [ADR-061](../Decisions/ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [Projection Model](../Specs/Projection-Model.md) · [Backtest Report](../Build-Plan/Backtest-Report.md) · [Testing levels](Testing-Levels.md)
