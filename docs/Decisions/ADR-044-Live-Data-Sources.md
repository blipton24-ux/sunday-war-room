---
title: "ADR-044: Live data from Sleeper plus the ESPN public scoreboard"
date: 2026-11-09
tags: [adr, data, live]
status: accepted
---
# ADR-044: Live data sources

## Context
Live win chance needs two things: each team's current fantasy points, and how much of each player's game is left. Sleeper's public API gives the points (already scored with the league's rules) but no game clock. Closes Open Question #8.

## Options considered (Sunday 1:20 pm, Matchup open)
| | Sleeper only | Scoreboard only, scored by us | **Sleeper + scoreboard** |
|---|---|---|---|
| Fantasy points | Sleeper's, with the league's rules | Ours, re-scored from play stats | Sleeper's |
| Quarter, clock, final | None | Yes | Yes |
| Win chance in Q4 | Can't tell Q1 from Q4 | Correct | Correct |
| Risk / work | Low / least | Unofficial feed / most | Only the clock part at risk / moderate |

For the clock itself: **ESPN's public scoreboard** (free, detailed, unofficial), a paid feed (official, monthly cost and an API key), or estimating from kickoff time (free, wrong during delays and overtime).

## Decision
**Sleeper for fantasy points, ESPN's public scoreboard for game state** (quarter, clock, possession, final). The scoreboard is unofficial, so it is loaded through one source module with a schema contract, like nflverse ([ADR-030](ADR-030-Stats-In-PostgreSQL.md)). If its shape changes or it fails, live win chance falls back to points only and the screen says so; nothing else breaks.

Related: [ADR-045 Live delivery](ADR-045-Live-Delivery-Polling.md) · [Open Questions](../Specs/Open-Questions.md) · [P2 Build Plan](../Build-Plan/P2-Build-Plan.md)
