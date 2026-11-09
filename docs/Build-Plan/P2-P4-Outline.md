---
title: "P2–P4 Outline"
date: 2026-11-08
tags: [build-plan]
---
# Phases 2–4 — outline

Each phase gets its own detailed plan, owner decisions and build after the previous phase is live ([ADR-026](../Decisions/ADR-026-Execution-Order.md)).

## P2 — Waivers, trades, live game day
- Decide: live delivery mechanism (polling / SSE / WebSockets), live score source ([Open Questions](../Specs/Open-Questions.md) #7–8).
- Rest-of-season value per player; free agents ranked by value added to your roster.
- Trade analyzer for both sides, plus trade suggestions.
- `poll_live_scores` job; live win probability; Matchup screen updates during games.
- Web push: VAPID keys, `push_subscriptions`, `send_push_alerts` job, iPhone install prompt.
- Model upgrades ([ADR-034](../Decisions/ADR-034-Ship-Model-v1-Upgrade-Later.md)): per-position expected-points models, depth-chart adjustments, defenses from betting totals, correlated simulation (QB ↔ own receivers). Each needs reuse approval (ADR-002) and must beat model 1.0.0 on held-out weeks, including the startable-player slice.

## P3 — AI assistant
- Decide: news sources, embedding provider, daily message limit ([Open Questions](../Specs/Open-Questions.md) #9–11).
- News ingestion + chunking + embeddings into pgvector; news badges on players.
- Agent loop in FastAPI: Claude via the Anthropic API with read-only tools (matchup, projections, waivers, trades, `search_news`); streaming responses to the Chat tab.
- Guardrails: quote verification, per-user limits, usage tracking, eval set of example questions with expected tool calls.

## P4 — ESPN + Yahoo
- ESPN adapter: secure cookie capture for a web app, encrypted at rest ([Open Questions](../Specs/Open-Questions.md) #12); ESPN scoring-rule coverage.
- Yahoo adapter: OAuth flow + token refresh; Yahoo scoring coverage.
- Goal: no feature code changes, only new adapters (the [adapter pattern](../Concepts/Adapter-Pattern.md) payoff).

Related: [P1 Build Plan](P1-Build-Plan.md) · [Features by Phase](../Specs/Features-by-Phase.md)
