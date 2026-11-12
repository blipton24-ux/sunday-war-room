---
title: "Features by Phase"
date: 2026-11-08
tags: [spec, product, planning]
---
# Features by Phase

Phasing: [ADR-009](../Decisions/ADR-009-Phasing.md). Each phase ships working and passing CI. Order after P2 ([ADR-049](../Decisions/ADR-049-Phases-Reordered-ESPN-First.md), [ADR-050](../Decisions/ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md)): P3 ESPN, P4 improved model, P5 AI assistant + strategy tendencies, P6 UI/UX overhaul, P7 Yahoo, P8 deploy + push alerts.

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

## P3 — ESPN (next)
Plan: [P3 Build Plan](../Build-Plan/P3-Build-Plan.md).
- **Connect by league link** ([ADR-051](../Decisions/ADR-051-ESPN-Access-Link-First-Cookie-Fallback.md)): public leagues connect with no login; private leagues use a guided screen to paste the two ESPN cookies, after which the user's leagues are listed and their team preselected. Phones get an "email me a link to finish on a computer" button.
- **Encrypted credentials** ([ADR-052](../Decisions/ADR-052-Credential-Encryption.md)); expired cookies pause only that user's league and show a reconnect banner.
- **Our own ESPN client** ([ADR-053](../Decisions/ADR-053-ESPN-Client-Own-Code.md)) with ESPN's scoring rules (every rule scored or explicitly reported as unsupported); head-to-head points leagues.
- Every existing feature (lineup, matchup, waivers, trades, live) works on an ESPN league.

## P4 — Improved model projections
The [ADR-034](../Decisions/ADR-034-Ship-Model-v1-Upgrade-Later.md) upgrades (per-position models, depth charts, correlated simulation), smarter rest-of-season projections, IDP players, dynasty/keeper future-season value. Each upgrade must beat the current model on held-out weeks.

## P5 — AI assistant + strategy tendencies
- **Chat tab:** Claude agent with read-only tools over Sunday War Room data plus news search (RAG) ([ADR-018](../Decisions/ADR-018-AI-Agent-With-RAG.md)).
- News ingestion + embeddings (pgvector); news badges on players.
- Per-user daily message limit; conversation history.
- **Strategy tendencies** (new scope): a manager's habits shown as badges and nudges. What it measures and where it appears are decided in the P5 plan.

## P6 — UI/UX overhaul
A full design pass over every screen so the app presents everything P1–P5 added coherently. Scope decided in the P6 plan.

## P7 — Yahoo
Yahoo adapter: OAuth "Sign in with Yahoo", token refresh (stored encrypted), Yahoo scoring coverage. Built right before deployment because Yahoo's sign-in needs an https return address and a real Yahoo league to verify against ([ADR-050](../Decisions/ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md)).

## P8 — Deploy + push alerts
Push alerts (starter ruled OUT, close matchup late, big swing; needs a real HTTPS address). Hosting platform, managed or self-run Postgres and Redis, `deploy.yml` (migrate, then roll out), domain and HTTPS, Google OAuth and Resend production setup, backups, live URL and screenshots in the README. Plan: [Later Phases Outline § P8](../Build-Plan/P2-P8-Outline.md#p8--deploy--push-alerts).

## Later / optional
Accuracy scoreboard vs external projections · paid tier (Stripe) ([ADR-011](../Decisions/ADR-011-Monetization.md)) · AWS + Terraform migration ([ADR-022](../Decisions/ADR-022-Hosting-Container-Platform.md)) · playoff odds simulation.

Related: [Product Vision](Product-Vision.md) · [P1 Build Plan](../Build-Plan/P1-Build-Plan.md) · [Later Phases Outline](../Build-Plan/P2-P8-Outline.md)
