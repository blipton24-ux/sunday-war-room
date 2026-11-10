---
title: "Features by Phase"
date: 2026-11-08
tags: [spec, product, planning]
---
# Features by Phase

Phasing: [ADR-009](../Decisions/ADR-009-Phasing.md). Each phase ships working and passing CI; improved model projections are Phase 5 and deployment Phase 6 ([ADR-043](../Decisions/ADR-043-Phases-Renumbered.md)).

## P1 — Sleeper MVP
- **Accounts:** sign in with Google or an email magic link; profile; sign out; delete account.
- **Connect Sleeper:** enter a Sleeper username → pick leagues for the current season → choose "my team" in each.
- **League switcher** for users in several leagues.
- **Sync:** on connect, hourly, and a "Refresh" button (queued job, "updated N min ago").
- **Projection model v1** from nflverse, scored with **each league's own scoring settings** ([Projection Model](Projection-Model.md)).
- **Lineup (start/sit):** recommended optimal lineup vs. current, swap suggestions, each player's projection with factors and an 80% range.
- **Matchup:** scoreboard with a **Projected to win** panel (winner, projected final, win chance) and starters side by side; scores as of last sync.
- **Home:** titled with the current week; matchup score header, Heads-up alerts (starter on bye/OUT, questionable, booming), "Fix my lineup", accuracy card.
- **PWA:** installable; dark-first theme with a light toggle; bottom tabs with a More menu.
- **Accuracy page (lightweight):** how Sunday War Room's frozen projections compared to actual results in past weeks.

## P2 — Waivers, trades, live game day (built 2026-11-10)
- **Waivers** ([ADR-047](../Decisions/ADR-047-Waivers-Value-Added.md)): free agents ranked by value added to *your* best lineup, rest of season or this week; suggested drop; waiver status under the league's rules; FAAB bid range.
- **Trade analyzer** ([ADR-048](../Decisions/ADR-048-Trades-Lineup-Impact.md)): any two teams, judged by lineup impact; "best for me, still acceptable" suggestions with an adjustable limit.
- **Live game day** ([ADR-044](../Decisions/ADR-044-Live-Data-Sources.md), [ADR-045](../Decisions/ADR-045-Live-Delivery-Polling.md)): scores, player game status, live projected finals and win chance, re-fetched every 30–60 s while games are live.
- **Any league** ([ADR-046](../Decisions/ADR-046-Any-League-Settings.md)): every waiver type, roster format and scoring setup. Plan: [P2 Build Plan](../Build-Plan/P2-Build-Plan.md).

## P3 — AI assistant
- **Chat tab:** Claude agent with read-only tools over Sunday War Room data plus news search (RAG) ([ADR-018](../Decisions/ADR-018-AI-Agent-With-RAG.md)).
- News ingestion + embeddings (pgvector); news badges on players.
- Per-user daily message limit; conversation history.

## P4 — ESPN + Yahoo
- **ESPN adapter:** private leagues need the user's `espn_s2`/`SWID` cookies, so a secure capture flow and encrypted storage are needed.
- **Yahoo adapter:** OAuth "Sign in with Yahoo" and token refresh.
- Scoring-rule coverage for each platform (every rule scored or explicitly reported as unsupported).

## P5 — Improved model projections
The [ADR-034](../Decisions/ADR-034-Ship-Model-v1-Upgrade-Later.md) upgrades (per-position models, depth charts, correlated simulation), smarter rest-of-season projections, IDP players, dynasty/keeper future-season value. Each upgrade must beat the current model on held-out weeks.

## P6 — Deploy + push alerts
Push alerts (starter ruled OUT, close matchup late, big swing; needs a real HTTPS address). Hosting platform, managed or self-run Postgres and Redis, `deploy.yml` (migrate, then roll out), domain and HTTPS, Google OAuth and Resend production setup, backups, live URL and screenshots in the README. Plan: [P2–P4 Outline § P5](../Build-Plan/P2-P4-Outline.md#p5--deploy).

## Later / optional
Accuracy scoreboard vs external projections · paid tier (Stripe) ([ADR-011](../Decisions/ADR-011-Monetization.md)) · AWS + Terraform migration ([ADR-022](../Decisions/ADR-022-Hosting-Container-Platform.md)) · playoff odds simulation.

Related: [Product Vision](Product-Vision.md) · [P1 Build Plan](../Build-Plan/P1-Build-Plan.md) · [P2–P4 Outline](../Build-Plan/P2-P4-Outline.md)
