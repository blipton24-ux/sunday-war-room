---
title: "ADR-072: One model, no blend with 1.0.0"
date: 2026-11-20
tags: [adr, model, machine-learning, p4]
status: accepted
---
# ADR-072: One model, no blend with 1.0.0

## Context
Backlog M-30: averaging the ML model with model 1.0.0 (80% and 20%) ordered players slightly better on 2022-2025 (rank accuracy 0.353 to 0.359, half PPR startable) at the same average miss (5.485 against 5.486); 90/10 gave 0.358 and 5.483. Measured on 2026-11-17, before the availability changes ([ADR-068](ADR-068-P4-Questionable-Players-Projected-If-Playing.md), [ADR-069](ADR-069-P4-Practice-Status-In-The-Model-News-Shown-Only.md)). A blend keeps 1.0.0's code running every week beside the new model.

## Options considered
**The same example:** the ML model says Puka Nacua 15.0, 1.0.0 says 13.0; an 80/20 blend shows 14.6.

| | **A: never blend** | B: test last in step 7e, keep only if it wins | C: blend 80/20 now |
|---|---|---|---|
| Number shown | 15.0 | 14.6 if the test keeps the blend, else 15.0 | 14.6 |
| Models run each week | one | one or two | two |
| 1.0.0 code for QB, RB, WR, TE | retired at 2.0.0 | kept only if the blend wins | kept |
| Explanations (step 9) | one model's reasons | possibly two | two |

## Decision
**Option A** (owner, 2026-11-20). Model 2.0.0 projects QB, RB, WR and TE with the ML model alone; 1.0.0's method for those positions is retired when 2.0.0 ships. Kickers and defenses keep the 1.0.0 method until step 12 replaces it ([P4 Build Plan](../Build-Plan/P4-Build-Plan.md)). The ordering gap to Sleeper's projections (M-28) is worked on through new signals (M-24, M-33).

## Why
The gain was small, measured on an earlier model, and costs a second model to maintain, freeze at kickoff and explain. One model keeps the Player screen's explanations exact.

## Trade-offs accepted
A possible ordering gain of about 0.006 in rank accuracy is not taken.

Related: [ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md) · [ADR-067](ADR-067-P4-Scope-For-The-Best-Model-Now.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md)
