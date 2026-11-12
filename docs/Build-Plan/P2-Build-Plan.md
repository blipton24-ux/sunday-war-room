---
title: "P2 Build Plan"
date: 2026-11-09
tags: [build-plan, p2]
---
# Phase 2 Build Plan: waivers, trades, live game day

Decisions: [ADR-043](../Decisions/ADR-043-Phases-Renumbered.md) (phases) · [ADR-044](../Decisions/ADR-044-Live-Data-Sources.md) (live data) · [ADR-045](../Decisions/ADR-045-Live-Delivery-Polling.md) (polling) · [ADR-046](../Decisions/ADR-046-Any-League-Settings.md) (any league) · [ADR-047](../Decisions/ADR-047-Waivers-Value-Added.md) (waivers) · [ADR-048](../Decisions/ADR-048-Trades-Lineup-Impact.md) (trades). Not in P2: push alerts and deploy (P8), model upgrades, IDP and dynasty value (P4); phase order per [ADR-049](../Decisions/ADR-049-Phases-Reordered-ESPN-First.md).

## Build order
Each step ends runnable, tested, committed and green in CI.

1. **Adapter additions** (done 2026-11-09): league waiver, trade and roster settings; transactions (to tell which dropped players are still on waivers); live matchup points. Recorded Sleeper fixtures for a FAAB and a priority league.
2. **Rest-of-season projections** (done 2026-11-09; through the fantasy playoffs, playoff weeks x1.5, no fading; 2.66 pts/week vs 2.77 naive on held-out 2025): this week's projection method carried across the remaining weeks with byes and opponents, per league scoring. Simple on purpose (smarter in P4). Backtest its error.
3. **Value engine** (done 2026-11-09; `app/model/value.py`, exact for any slot mix, cross-checked against the lineup optimizer; 12-team league: waivers 0.24 s, trade ideas 2.6 s): best lineup over a set of players, summed over the remaining weeks: value added (waivers) and lineup impact (trades). Pure functions, tested on superflex, 2QB, IR, taxi and K/DEF-off rosters.
4. **Waivers** (done 2026-11-10): status per waiver type, ranking with the this-week / rest-of-season toggle, suggested drop, FAAB bid range; `GET /leagues/{id}/waivers?horizon=`; Waivers screen.
5. **Trade analyzer** (done 2026-11-10): `POST /leagues/{id}/trades/evaluate` (any two teams); `GET /leagues/{id}/trades/suggestions?max_loss=`; Trades screen with team pickers, before/after lineups and the "acceptable" slider.
6. **ESPN scoreboard source** (done 2026-11-10; `app/sources/espn_scoreboard.py`, recorded real weeks 9-10 plus a derived live file): one module with a schema contract; team codes mapped to ours.
7. **Live game day** (done 2026-11-10; every-minute worker tick that does nothing outside game windows; Matchup polls every 45 s while live; kickoff-time estimate when the scoreboard is down): a worker job polls Sleeper and the scoreboard during game windows; live win chance from the remaining share of each game; player status on Matchup and Home; screens re-fetch every 30–60 s only while games are live; points-only fallback when the scoreboard fails.
8. **Tests and docs** (done 2026-11-10): specs for waivers, trades and live; OpenAPI and generated client; vault, Verification Gaps, backlog. Changed from the plan: the end-to-end world stores the scoreboard rows the live tick would write, instead of a stand-in server replaying a Sunday (the worker's cron is off in that stack); the tick itself is tested against a fake scoreboard in `test_live.py`.

## Verification checklist
- [x] Waivers rank free agents for a FAAB league and a priority league; status and bid range follow each league's settings. (`tests/integration/test_waivers.py`; on a real league: V-33, V-34)
- [x] The toggle switches between rest of season and this week; a suggested drop is shown. (`e2e/waivers.spec.ts`, `test_full_roster_suggests_a_drop`)
- [x] A trade between any two teams shows both teams' lineups before and after; a 2-for-1 is only a win if the extra player starts. (`test_two_for_one_only_counts_the_second_player_if_he_starts`, `e2e/trades.spec.ts`)
- [x] Suggestions respect the "acceptable" limit. (`test_suggestions_help_me_and_respect_the_limit`)
- [x] During a simulated live Sunday, scores, player status and win chance blend points so far with time left, and the screen re-polls while live; the worker does nothing outside game windows. (`test_live.py`, `e2e/live.spec.ts`; a real Sunday is V-35)
- [x] If the scoreboard breaks, scores still update and time left is estimated from kickoff, and the screen says so. (`test_scoreboard_down_still_updates_points`, `test_without_the_scoreboard_time_left_comes_from_kickoff`)
- [x] Rest-of-season backtest numbers recorded in the [Backtest Report](Backtest-Report.md).
- [x] pytest, Vitest and Playwright pass locally and in GitHub Actions. (260 / 73 / 81; CI green on "P2 step 8", 2026-11-10)

Related: [P1 Build Plan](P1-Build-Plan.md) · [Later Phases Outline](P2-P8-Outline.md) · [Features by Phase](../Specs/Features-by-Phase.md)
