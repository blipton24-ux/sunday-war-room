---
title: "Model Experiments"
date: 2026-11-12
tags: [build-plan, model, backtest]
---
# Model experiments (P4)

One row per idea, kept or dropped, with its numbers. Rules: [ADR-054](../Decisions/ADR-054-P4-Test-Every-Idea-One-At-A-Time.md) (how ideas are tested) and [ADR-055](../Decisions/ADR-055-P4-Keep-Rule.md) (when one is kept). Dropped ideas stay here so they are not retried blindly.

Columns: **Tuning** = change in startable-player average miss on 2022–2024 (negative is better), **Check** = the same on 2025, **Worst position** = the biggest loss at any position, **Verdict** = kept, kept for named positions, dropped, or noise.

| ID | Idea | Group | Data needed | Tuning | Check | Worst position | Verdict | Version |
|---|---|---|---|---|---|---|---|---|
| E-00 | Baseline: model 1.0.0 | | | n/a | n/a | n/a | incumbent | 1.0.0 |
| E-01 | Leave injury-spoiled games out of a player's own history (`skip-injury-history`) | E / D | nflverse injury reports, rosters | +0.016 (worse, beyond chance) | -0.002 (noise) | RB +0.020 (tuning) | **dropped** | n/a |

Groups follow the [P4 Build Plan](P4-Build-Plan.md): A opportunity · B defense by position · C offense quality · D role and depth · E injuries · F game conditions · G kickers and defenses · H how pieces combine · I ranges and win chance.

## Notes

**E-01** (2026-11-12, full PPR, startable players, weeks 5+, injury games left out): the idea was that a 2-point game caused by an injury should not drag down a player's later projections. On the tuning seasons (2022-2024) the change was +0.016 points, an interval of +0.001 to +0.031, so slightly worse; on 2025 it was -0.002 (-0.020 to +0.016), noise; no position moved by more than 0.02. A plausible reason: games where a player was hurt are honest evidence that he gets hurt, and dropping them loses information. Not retried unless the injury rule changes.

Related: [P4 Build Plan](P4-Build-Plan.md) · [Backtest Report](Backtest-Report.md) · [Improvement Backlog](Improvement-Backlog.md)
