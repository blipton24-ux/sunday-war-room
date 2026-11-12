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

Groups follow the [P4 Build Plan](P4-Build-Plan.md): A opportunity · B defense by position · C offense quality · D role and depth · E injuries · F game conditions · G kickers and defenses · H how pieces combine · I ranges and win chance.

Related: [P4 Build Plan](P4-Build-Plan.md) · [Backtest Report](Backtest-Report.md) · [Improvement Backlog](Improvement-Backlog.md)
