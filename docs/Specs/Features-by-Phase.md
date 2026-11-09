---
title: "Features by Phase"
date: 2026-11-08
tags: [spec, product, planning]
---
# Features by Phase

Phasing: [ADR-009](../Decisions/ADR-009-Phasing.md). Each phase ships working and passing CI; deployment is Phase 5 ([ADR-042](../Decisions/ADR-042-Deploy-As-Phase-5.md)).

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

## P2 — Waivers, trades, live game day
- **Waivers:** free agents ranked by projected value added to *your* roster (rest of season and this week).
- **Trade analyzer:** evaluate any proposed trade for both sides; suggest fair trades.
- **Live dashboard:** scores updating during games (~1 min), win probability moving live. Delivery mechanism (polling vs Server-Sent Events vs WebSockets) to be decided in the P2 spec.
- **Push alerts:** starter ruled OUT, close matchup late, big swing.

## P3 — AI assistant
- **Chat tab:** Claude agent with read-only tools over Sunday War Room data plus news search (RAG) ([ADR-018](../Decisions/ADR-018-AI-Agent-With-RAG.md)).
- News ingestion + embeddings (pgvector); news badges on players.
- Per-user daily message limit; conversation history.

## P4 — ESPN + Yahoo
- **ESPN adapter:** private leagues need the user's `espn_s2`/`SWID` cookies, so a secure capture flow and encrypted storage are needed.
- **Yahoo adapter:** OAuth "Sign in with Yahoo" and token refresh.
- Scoring-rule coverage for each platform (every rule scored or explicitly reported as unsupported).

## P5 — Deploy
Hosting platform, managed or self-run Postgres and Redis, `deploy.yml` (migrate, then roll out), domain and HTTPS, Google OAuth and Resend production setup, backups, live URL and screenshots in the README. Plan: [P2–P4 Outline § P5](../Build-Plan/P2-P4-Outline.md#p5--deploy).

## Later / optional
Accuracy scoreboard vs external projections · paid tier (Stripe) ([ADR-011](../Decisions/ADR-011-Monetization.md)) · AWS + Terraform migration ([ADR-022](../Decisions/ADR-022-Hosting-Container-Platform.md)) · playoff odds simulation.

Related: [Product Vision](Product-Vision.md) · [P1 Build Plan](../Build-Plan/P1-Build-Plan.md) · [P2–P4 Outline](../Build-Plan/P2-P4-Outline.md)
