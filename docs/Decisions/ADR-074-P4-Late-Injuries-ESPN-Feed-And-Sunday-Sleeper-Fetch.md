---
title: "ADR-074: Late injuries: ESPN's injury feed near each kickoff, and Sunday's Sleeper fetch after inactives"
date: 2026-11-20
tags: [adr, model, injuries, data-source, live, p4]
status: accepted
---
# ADR-074: Late injuries: ESPN's injury feed near each kickoff, and Sunday's Sleeper fetch after inactives

## Context
Injury status comes from Sleeper's player list, fetched once a day at 09:15 UTC (`sync_players_job`); Sleeper asks for at most one full-list fetch a day. Teams name inactives 90 minutes before kickoff, and projections freeze at kickoff, so a player ruled out on Sunday morning is frozen as if he plays (backlog M-10; the earlier project traced about 0.26 of a 0.45-point gap to ESPN to this).

Checked 2026-11-20: ESPN's public per-team injuries feed (`sports.core.api.espn.com/v2/sports/football/leagues/nfl/teams/{id}/injuries`) answers without sign-in and links each listed player's current entry, about 150-200 small requests for a full check. The ESPN league adapter (P3) receives `injuryStatus` for rostered players, but only for ESPN leagues.

## Options considered
**The same example:** Puka Nacua is Questionable; at 11:30 Eastern on Sunday the Rams list him inactive.

| | A: ESPN feed on game days | B: Sunday's Sleeper fetch after inactives | **C: both** |
|---|---|---|---|
| How | poll the teams kicking off within about two hours, every 15 minutes | move Sunday's one daily fetch to about 11:45 Eastern | A for every window, B as a safety net |
| 1 PM games | covered | covered | covered |
| Late, Thursday and Monday games | covered | not covered | covered |
| If ESPN changes its feed | late inactives missed | n/a | 1 PM games still covered |

## Decision
**Option C** (owner, 2026-11-20).
- On game days the worker polls ESPN's injury feed for teams kicking off within about two hours, every 15 minutes, and recomputes projections for players whose status changed, before the kickoff freeze. Each status change is recorded in `player_status_snapshots`, like Sleeper's.
- Sunday's Sleeper player-list fetch moves to about 11:45 Eastern (still once a day); other days keep the morning fetch.
- When the two sources disagree, the newer report wins; a failed ESPN poll changes nothing and is logged.
- Whether ESPN shows inactives in time is checked on a real Sunday (Verification Gaps).

## Why
Every kickoff window is covered, and the busiest one stays covered without ESPN. Polling only teams about to play keeps requests low exactly when they matter.

## Trade-offs accepted
A second undocumented ESPN endpoint (beside the scoreboard, [ADR-045](ADR-045-Live-Delivery-Polling.md), and the news feed, [ADR-069](ADR-069-P4-Practice-Status-In-The-Model-News-Shown-Only.md)), which may change without notice; a few thousand small requests on a Sunday.

Related: [ADR-068](ADR-068-P4-Questionable-Players-Projected-If-Playing.md) · [ADR-069](ADR-069-P4-Practice-Status-In-The-Model-News-Shown-Only.md) · [ADR-045](ADR-045-Live-Delivery-Polling.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md)
