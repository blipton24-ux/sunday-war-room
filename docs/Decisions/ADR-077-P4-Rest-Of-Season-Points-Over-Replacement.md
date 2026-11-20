---
title: "ADR-077: Rest-of-season value shown as points over the last starter; the long-range model only if needed"
date: 2026-11-20
tags: [adr, model, trades, waivers, rest-of-season, p4]
status: accepted
---
# ADR-077: Rest-of-season value shown as points over the last starter; the long-range model only if needed

## Context
Rest-of-season value is the weekly model carried across the remaining schedule ([ADR-047](ADR-047-Waivers-Value-Added.md), [ADR-048](ADR-048-Trades-Lineup-Impact.md); playoff weeks count 1.5 times, owner 2026-11-09). With 1.0.0 as the weekly model, held-out 2025, it lost slightly to a naive season average at RB (2.86 against 2.78) and TE (1.96 against 1.95) (backlog M-15). P4 step 13 planned a separate long-range model. Waivers and trades already rank by lineup impact, which compares against the manager's own roster; there is no per-player value that compares positions on one scale.

## Options considered
**The same example:** Puka Nacua, 15.2 points a week for the rest of the season, in a 12-team half-PPR league starting three receivers.

What "replacement" means:

| | A: best free agent in the league | **B: last starter league-wide** | C: average starter |
|---|---|---|---|
| Baseline | 8.1 | **9.0** (the 36th receiver) | 11.5 |
| Puka | +7.1 a week | **+6.2 a week** | +3.7 a week |
| Shows | what can be picked up today | how scarce he is across the league | stud or ordinary starter |

The long-range model: A build it regardless; **B first measure 2.0.0 carried across the schedule and build it only if a position still loses to the naive average**; C drop step 13.

## Decision
Owner, 2026-11-20:
- **Points over replacement, replacement = the last starter league-wide (B).** For each position, the replacement is the player ranked at (teams x that position's starting slots), counting flex slots: every team's dedicated slots are filled first, then each flex slot goes to the highest-projected eligible player left. Values use the league's own scoring and rest-of-season points per week.
- It is **shown** beside each player on the trade, waiver and Player screens ("+6.2 a week over the last starting WR"). Suggestions keep ranking by lineup impact (ADR-047, ADR-048), which also counts roster spots.
- **Step 13 measures first (B).** After 2.0.0 ships, the rest-of-season backtest is rerun with 2.0.0 carried across the schedule; a separate long-range model is built only if a position still loses to the naive average, and ships only under [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md)'s rule.

## Why
The last starter is the standard way to put every position on one scale: it measures how much a player beats what every team has to start anyway. Measuring before building avoids a second model that the better weekly model may already make unnecessary.

## Trade-offs accepted
The value ignores what is actually on a league's waivers (a deep league's waivers may hold players near the baseline); lineup impact, which the rankings use, still covers the manager's real alternatives.

Related: [ADR-047](ADR-047-Waivers-Value-Added.md) · [ADR-048](ADR-048-Trades-Lineup-Impact.md) · [ADR-046](ADR-046-Any-League-Settings.md) · [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md)
