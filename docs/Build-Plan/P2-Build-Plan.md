---
title: "P2 Build Plan"
date: 2026-11-09
tags: [build-plan, p2]
---
# Phase 2 Build Plan: waivers, trades, live game day

Decisions: [ADR-043](../Decisions/ADR-043-Phases-Renumbered.md) (phases) · [ADR-044](../Decisions/ADR-044-Live-Data-Sources.md) (live data) · [ADR-045](../Decisions/ADR-045-Live-Delivery-Polling.md) (polling) · [ADR-046](../Decisions/ADR-046-Any-League-Settings.md) (any league) · [ADR-047](../Decisions/ADR-047-Waivers-Value-Added.md) (waivers) · [ADR-048](../Decisions/ADR-048-Trades-Lineup-Impact.md) (trades). Not in P2: push alerts and deploy (P6), model upgrades, IDP and dynasty value (P5).

## Build order
Each step ends runnable, tested, committed and green in CI.

1. **Adapter additions:** league waiver, trade and roster settings; transactions (to tell which dropped players are still on waivers); live matchup points. Recorded Sleeper fixtures for a FAAB and a priority league.
2. **Rest-of-season projections:** this week's projection method carried across the remaining weeks with byes and opponents, per league scoring. Simple on purpose (smarter in P5). Backtest its error.
3. **Value engine:** best lineup over a set of players, summed over the remaining weeks: value added (waivers) and lineup impact (trades). Pure functions, tested on superflex, 2QB, IR, taxi and K/DEF-off rosters.
4. **Waivers:** status per waiver type, ranking with the this-week / rest-of-season toggle, suggested drop, FAAB bid range; `GET /leagues/{id}/waivers?horizon=`; Waivers screen.
5. **Trade analyzer:** `POST /leagues/{id}/trades/evaluate` (any two teams); `GET /leagues/{id}/trades/suggestions?max_loss=`; Trades screen with team pickers, before/after lineups and the "acceptable" slider.
6. **ESPN scoreboard source:** one module with a schema contract; team codes mapped to ours.
7. **Live game day:** a worker job polls Sleeper and the scoreboard during game windows; live win chance from the remaining share of each game; player status on Matchup and Home; screens re-fetch every 30–60 s only while games are live; points-only fallback when the scoreboard fails.
8. **Tests and docs:** end-to-end stand-ins (Sleeper and a scoreboard replaying a recorded Sunday), specs for waivers, trades and live; OpenAPI and generated client; vault, Verification Gaps, backlog.

## Verification checklist
- [ ] Waivers rank free agents for a FAAB league and a priority league; status and bid range follow each league's settings.
- [ ] The toggle switches between rest of season and this week; a suggested drop is shown.
- [ ] A trade between any two teams shows both teams' lineups before and after; a 2-for-1 is only a win if the extra player starts.
- [ ] Suggestions respect the "acceptable" limit.
- [ ] During a simulated live Sunday, scores, player status and win chance change between polls; nothing polls when no game is live.
- [ ] If the scoreboard breaks, win chance falls back to points only and says so.
- [ ] Rest-of-season backtest numbers recorded in the [Backtest Report](Backtest-Report.md).
- [ ] pytest, Vitest and Playwright pass locally and in GitHub Actions.

Related: [P1 Build Plan](P1-Build-Plan.md) · [P2–P4 Outline](P2-P4-Outline.md) · [Features by Phase](../Specs/Features-by-Phase.md)
