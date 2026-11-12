---
title: "ADR-054: P4 tests every model idea on past seasons, one at a time"
date: 2026-11-12
tags: [adr, model, process]
status: accepted
---
# ADR-054: P4 tests every idea on past seasons, one at a time

## Context
Model 1.0.0 is close to a plain season average ([ADR-034](ADR-034-Ship-Model-v1-Upgrade-Later.md)). Many ideas could improve it: opportunity (target share, share of carries), defenses split by run and pass against each position, offense quality, depth charts, injuries, game conditions and more. Testing many ideas against the same past games has a known trap: with enough ideas, some "win" by luck.

## Options considered
| Option | Result |
|---|---|
| **One idea at a time, each behind a switch, judged on separate sets of seasons** | Every idea's effect is visible on its own; luck is caught by the check season and fresh weeks |
| One large rewrite, judged once | Fast, but a bad part hides inside a good whole |
| Add only the few best-known ideas | Safe, but leaves untested ideas unmeasured |

## Decision
Every idea is built behind a switch (`ModelConfig`), compared against the current best on the **tuning seasons** (2022–2024), and confirmed on the **check season** (2025). Kept ideas are grouped into a numbered model version. Each version gets one look at **fresh weeks** (2026 so far, never used while tuning) before it ships; a version that wins on 2025 but loses on the fresh weeks does not ship. Every idea, kept or dropped, is written in the [experiment ledger](../Build-Plan/Model-Experiments.md).

**Injury-affected games do not count in backtests.** A player hurt before or during a game scores for a reason no model could know. The backtest marks those games and leaves them out of the headline numbers; it prints the "everything counted" numbers and the count of games left out next to it. The marking rule is fixed before experiments start and is never tuned afterwards. Those games are also left out of a player's own history when projecting later weeks, as an experiment like any other.

## Why
The check season and fresh weeks are the defence against fooling ourselves. The injury rule keeps one-off accidents from rewarding or punishing an idea.

## Trade-offs accepted
Slower than a rewrite. Fresh weeks mean a version waits for enough 2026 games before it can ship.

Related: [ADR-034](ADR-034-Ship-Model-v1-Upgrade-Later.md) · [ADR-055](ADR-055-P4-Keep-Rule.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Projection Model](../Specs/Projection-Model.md)
