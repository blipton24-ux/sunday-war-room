---
title: "ADR-064: Predicted stats are scored spread-aware"
date: 2026-11-16
tags: [adr, model, machine-learning, scoring, p4]
status: accepted
---
# ADR-064: Predicted stats are scored spread-aware

## Context
The machine-learning model ([ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md)) predicts each player's **expected** stats, then each league's own rules score them. Linear rules (0.1 points per yard) give the same points whether they score one average or many games. Two kinds of rule do not:
- **Step rules**, such as ESPN's "1 point per full 10 receiving yards" (`espn:REY10`, used by one of the owner's leagues, with `PY25` and `RY10`): scoring an average of 66 yards gives 6, while real games around that average give about 6.1, and an average of 59.9 gives 5 instead of about 5.5.
- **Tier bonuses**, such as "+3 for 100 receiving yards": an average under 100 scores nothing, even when the player clears 100 in about one game in six.
Model 1.0.0 never had this problem because it averaged points already scored game by game.

## Options considered

**The same example through each option:** Puka Nacua, about 66 expected receiving yards, in a league with 1 point per full 10 receiving yards and a +3 bonus at 100.

| | A: score the averages | **B: spread-aware** | C: simulate games |
|---|---|---|---|
| How | Plug 66 yards into the rules | Learn how spread out each stat is around its prediction; score step and bonus rules at their expected value under that spread | Score about 2,000 simulated stat lines per player and average |
| Per-10-yards rule | 6.0 | about 6.1 | about 6.1 |
| 100-yard bonus | 0 | about +0.47 | about +0.47 |
| Linear leagues | exact | exact (unchanged) | exact, slower |
| Work and speed | none, instant | moderate, instant | large (a full shape for every stat; overlaps the range method of P4 step 8), slower |

## Decision
**Option B** (owner, 2026-11-16).
- `scoring.score(df, rules, variance)`: given each stat's variance, step, tier and range rules score their expected value under a **gamma** distribution (non-negative, long right tail) with the predicted mean and that variance (`expected_rule`). Linear rules, per-position overrides and every other path are unchanged; without `variance`, scoring is exactly as before.
- The variance comes from a **spread** per position and stat, `variance = a x expected^b`, fit out of sample: the models trained without the last training season predict it, and real stats are compared with those predictions (`ml/project.py`, `fit_spreads`). Too little data: variance = expected (Poisson).

## Why
It fixes the owner's ESPN league and any bonus league, is exact for linear leagues, and stays fast and simple. Its result matches a brute-force simulation (66 yards, spread 35: 6.10 against 6.10, bonus 0.47 against 0.466).

## Trade-offs accepted
Each rule is scored on one quantity's spread at a time, and a sum such as rushing plus receiving yards takes the sum of the two variances (treated as independent). The spread is fit on one held-back season per training run. Option C stays open if the backtest shows the gamma shape is off for some stat.

Related: [ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md) · [ADR-053](ADR-053-ESPN-Client-Own-Code.md) · [ADR-031](ADR-031-Approved-Reuses.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Projection Model](../Specs/Projection-Model.md)
