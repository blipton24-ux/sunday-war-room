---
title: "ADR-061: How the machine-learning model is tested and shipped"
date: 2026-11-14
tags: [adr, model, machine-learning, process, p4]
status: accepted
---
# ADR-061: How the machine-learning model is tested and shipped

Goes with [ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md) (the model). Carries over what still holds from the first P4 approach's testing rules (ADR-054 and ADR-055, removed 2026-11-14) and fixes what a review of that approach found.

## Context
A model that learns from data will always look good on the games it learned from. The only honest number is its miss on games it never saw while being built. The first P4 approach used three fixed sets: tune on 2022-2024, check on 2025, one look at 2026. A review (2026-11-14) found:

1. **2025 had been looked at many times** (round 1 sweep, six round 1 tuners, round 2 per position), so "passes on 2025" had become weaker evidence.
2. **Average miss is not the same as start/sit quality.** A model can lower its average miss by pulling every player toward the middle while getting the order of players worse. Nothing measured order.
3. **A fixed "keep it" threshold (0.004 points) ignored noise.** Some positions are far noisier than others.
4. **Every comparison was against our own models.** Nothing showed whether the app beats a projection users already see elsewhere.
5. **The headline left injury-spoiled games out.** That is right for judging a model, but users live with those misses.

## Options considered

**The same scenario through each option:** deciding whether model 2.0.0 is better than 1.0.0 for wide receivers.

| Option | How 2.0.0 is judged | What can go wrong |
|---|---|---|
| Fixed sets (the first approach) | Settings picked on 2022-2024; checked on 2025; one look at 2026 | 2025 wears out after many looks; one season is a small sample |
| **Season-by-season walk-forward, tuning inside the training seasons** | To test 2023, train on seasons up to 2022 and pick settings using only those seasons; repeat for 2022, 2024 and 2025. Every test season is unseen by both training and setting choices; 2026 stays the one-look final check | Slower to run (four trainings per check), so the model must train in minutes |
| Mixed seasons (train on 2022, 2023 and 2025 to test 2024) | Uses more data per test | Learns from the future: 2025 trends leak into a 2024 test, so the number is too optimistic for a live app that never has next season's data |

## Decision
1. **Season-by-season walk-forward.** The test seasons are 2022, 2023, 2024 and 2025. For each, the model trains only on earlier seasons and is applied week by week, with the current season's earlier weeks added as it goes, exactly as it would run live.
2. **Model settings are chosen inside the training seasons only** (the last training season is held back to pick tree depth, learning rate, number of trees and the like, with early stopping). No test season ever influences a setting, so each of the four stays honest however many times the model is rebuilt.
3. **2026 weeks played so far are the final check**, looked at once per version, before it ships.
4. **What decides "ship":** against the live model, on startable players (each week's top 15 QB and TE, top 36 RB and WR, picked by plain season average so both models are graded on the same players), all weeks:
   - better beyond chance over the four test seasons pooled (paired bootstrap over weeks, the whole 95% interval below zero);
   - better in at least three of the four test seasons on its own;
   - no position worse by more than 0.05 points pooled (kickers and defenses graded on all their games);
   - not worse on the 2026 weeks.
5. **Noise-aware changes while building.** A new signal or setting is kept only if its gain on the training-side check is larger than that position's bootstrap noise, not a fixed number.
6. **Injury-spoiled games** are marked by the fixed evidence-based rule (`api/app/model/features/injury_games.py`; never tuned) and left out of the number that decides. **"Everything counted" is always shown beside it**, and it is the number the Accuracy page and any public claim lead with.
7. **Reported every time, but not part of the ship decision:** rank accuracy (how well each week's projected order at a position matches the actual order, Spearman correlation), range coverage (the 80% range should contain about 80% of results, per position and scoring format), weeks 1-4 and 5+ apart, and rest-of-season accuracy (must not get worse, carried over from ADR-057).
8. **Benchmarks in every report:** plain season average, model 1.0.0, the published numbers of the removed 1.1.0, and, if a historical source can be found and is approved as a data source, Sleeper's own weekly projections (benchmark only, never a model input).

## Why
Walk-forward by season mirrors how the app runs: it only ever knows the past. Choosing settings inside the training seasons means the test seasons never wear out, which was the first approach's main weakness. Four test seasons instead of one make "better" much harder to get by luck. Rank accuracy and an outside benchmark measure what users actually care about: making the right start/sit call, and beating the projection they already have.

## Trade-offs accepted
Four trainings per check take longer than one; the model must train in minutes, which XGBoost does on this data. A model can pass the ship rule and still rank players slightly worse; rank accuracy is reported so that would be seen, and it can be promoted into the rule later if it disagrees with average miss.

Related: [ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md) · [ADR-034](ADR-034-Ship-Model-v1-Upgrade-Later.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Backtest Report](../Build-Plan/Backtest-Report.md) · [Machine learning and XGBoost](../Concepts/Machine-Learning-and-XGBoost.md)
