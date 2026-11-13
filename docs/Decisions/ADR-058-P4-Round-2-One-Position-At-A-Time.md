---
title: "ADR-058: P4 round 2 tunes one position at a time; kept is judged on all weeks"
date: 2026-11-12
tags: [adr, model, process]
status: accepted
---
# ADR-058: Round 2 tunes one position at a time; kept is judged on all weeks

Amends [ADR-055](ADR-055-P4-Keep-Rule.md) (which slice decides) and refines [ADR-054](ADR-054-P4-Test-Every-Idea-One-At-A-Time.md) (how ideas are searched).

## Context
Round 1 ([ledger](../Build-Plan/Model-Experiments.md)) ran six tuners side by side, one per position, on a coarse grid. Each position's settings were already judged on that position alone, but the search was shallow: each idea was first looked at at one or two strengths with every position graded together, some ideas were offered only to some positions, five ideas were deferred, and nothing was specific to a position. Positions are scored and projected differently (a quarterback's points come mostly from passing, a running back's from carries and short catches, a kicker's from his team stalling in range), so the ideas that matter differ by position.

Round 1 also left open which weeks decide "kept": RB, WR, TE and DEF beat the shipped model on all weeks together on both sets of seasons, but only TE also did so on weeks 5+ alone.

## Options considered
| Option | Result |
|---|---|
| **Deeper pass, one position at a time** | Every idea at every strength on that position alone, ideas specific to the position, a finer tuner, a review before the next position. Slower; more to see |
| Re-run round 1's tuners in sequence | Quick, but close to round 1's results |
| Keep round 1 as final | Leaves the deferred and position-specific ideas untested |

| Slice that decides "kept" | Result |
|---|---|
| **All weeks together** | Weeks 1-4 matter for real lineups too; keeps RB, WR, TE, DEF from round 1 |
| Weeks 5+ only | Stricter; keeps only TE from round 1 |

## Decision
1. **One position at a time**, in the order RB, WR, TE, QB, DEF, K, with the owner reviewing each position's results before the next starts. For each position:
   - **Sweep:** every idea at every strength, alone against the shipped model, on the tuning seasons (2022-2024) only.
   - **Tune:** combine the ideas, starting from the sweep's best values, then refine the winners between grid points.
   - **Check:** open 2025 once for the tuned settings.
2. **Ideas in round 2:** round 1's settings for that position, the five deferred ideas (nflverse expected points, depth-chart rank, teammate out, first games back from injury; fitted injury discounts get their own test), and new ideas specific to the position, listed for the owner before they are built.
3. **Kept is judged on all weeks together** on both sets of seasons. Weeks 1-4 and weeks 5+ are still reported, and a gain that exists only in one of them is recorded as such. The other parts of ADR-055 stand: beyond chance, and no position worse by more than 0.05 (automatic here, since each position's settings touch only that position).
4. **The 2026 weeks played so far are the final check**, once per version, before anything ships.

## Why
2025 was already opened once per position in round 1. A second round checked on 2025 gives a second look at the same games, so a winner on 2025 alone is weaker evidence than it was in round 1. The 2026 weeks have never been used to choose anything and stay that way. A deeper search also finds more settings that only fit 2022-2024 by luck; QB and K in round 1 showed exactly that. The check seasons are what catch it, so they are never used to pick a value.

## Trade-offs accepted
More compute (about an hour or more per position, even run in parallel) and a pause after every position. Ideas that need data the live app does not load yet (betting lines, depth charts, air yards) can be kept in the backtest but cannot ship until that data is loaded live ([backlog](../Build-Plan/Improvement-Backlog.md) M-22).

Related: [ADR-054](ADR-054-P4-Test-Every-Idea-One-At-A-Time.md) · [ADR-055](ADR-055-P4-Keep-Rule.md) · [Model Experiments](../Build-Plan/Model-Experiments.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md)
