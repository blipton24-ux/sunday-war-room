---
title: "Later Phases Outline (P2–P8)"
date: 2026-11-08
tags: [build-plan]
---
# Phases 2–8 — outline

Each phase gets its own detailed plan, owner decisions and build after the previous phase is done ([ADR-026](../Decisions/ADR-026-Execution-Order.md)). Order after P2: [ADR-049](../Decisions/ADR-049-Phases-Reordered-ESPN-First.md), amended by [ADR-050](../Decisions/ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md). (The file keeps its old name so existing links still work.)

## P2 — Waivers, trades, live game day
Built 2026-11-10: [P2 Build Plan](P2-Build-Plan.md). Push alerts moved to P8 and model upgrades to P4.

## P3 — ESPN (next)
Decided and planned: [P3 Build Plan](P3-Build-Plan.md) ([ADR-051](../Decisions/ADR-051-ESPN-Access-Link-First-Cookie-Fallback.md) access, [ADR-052](../Decisions/ADR-052-Credential-Encryption.md) encryption, [ADR-053](../Decisions/ADR-053-ESPN-Client-Own-Code.md) client). Yahoo moved to P7 ([ADR-050](../Decisions/ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md)). Every P2 feature (waivers, trades, live) must work on the owner's ESPN league.

## P4 — Improved model projections
Decided and planned: [P4 Build Plan](P4-Build-Plan.md) ([ADR-054](../Decisions/ADR-054-P4-Test-Every-Idea-One-At-A-Time.md) to [ADR-057](../Decisions/ADR-057-P4-Scope-Weekly-Accuracy.md)). Weekly accuracy only: rest-of-season, IDP and keeper/dynasty moved out of P4 (ADR-057). The paragraph below is the earlier outline.

The [ADR-034](../Decisions/ADR-034-Ship-Model-v1-Upgrade-Later.md) upgrades (per-position expected-points models, depth-chart adjustments, defenses from betting totals, correlated simulation), smarter rest-of-season projections, IDP players, dynasty/keeper future value. Each needs reuse approval (ADR-002) and must beat model 1.0.0 on held-out weeks, including the startable-player slice.

## P5 — AI assistant + strategy tendencies
- Decide: news sources, embedding provider, daily message limit ([Open Questions](../Specs/Open-Questions.md) #9–11).
- News ingestion + chunking + embeddings into pgvector; news badges on players.
- Agent loop in FastAPI: Claude via the Anthropic API with read-only tools (matchup, projections, waivers, trades, `search_news`); streaming responses to the Chat tab.
- Guardrails: quote verification, per-user limits, usage tracking, eval set of example questions with expected tool calls.
- **Strategy tendencies** (new scope): decide what a manager's tendencies are measured from, where badges and nudges appear, and whether anything is reused from earlier projects (ADR-002).

## P6 — UI/UX overhaul
- Decide the scope: which screens change, navigation for the features P3–P5 added, design-system cleanup. Any change to the flat Sunday War Room look ([ADR-032](../Decisions/ADR-032-Visual-Sunday-War-Room-Style.md)) is an owner decision.
- Open UI rows in the [Improvement Backlog](Improvement-Backlog.md) are the starting list.
- Accessibility stays at WCAG 2.1 AA ([ADR-041](../Decisions/ADR-041-Accessibility-Standard.md)); E2E tests updated with the screens.

## P7 — Yahoo
- Yahoo adapter: OAuth flow + token refresh (tokens stored with the P3 encryption, [ADR-052](../Decisions/ADR-052-Credential-Encryption.md)); Yahoo scoring coverage.
- Needs a Yahoo developer app, an https redirect address and a Yahoo league to verify against, which is why it sits next to deployment ([ADR-050](../Decisions/ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md)). Goal: only a new adapter and an OAuth flow, because P3 made the rest platform-neutral.

## P8 — Deploy + push alerts
Moved here from P1 step 16 ([ADR-042](../Decisions/ADR-042-Deploy-As-Phase-5.md); P8 since ADR-050), the last phase.
- Push alerts: VAPID keys, `push_subscriptions`, `send_push_alerts` job (starter ruled OUT, close matchup late, big swing), iPhone install prompt.
- Re-decide the platform and domain against current prices ([Open Questions](../Specs/Open-Questions.md) #1–2); verify pgvector support on whatever hosts Postgres.
- Staging deploy first, then production; `deploy.yml` on merge to main (migrate, then roll out); HTTPS; backups with a tested restore.
- Production Google OAuth and Resend domain; trusted proxy header for rate limits (P-13); worker health check (P-10).
- Close the deploy-dependent Verification Gaps (V-18, V-23 to V-27, V-30) and P-07 (sign-in in an installed iPhone app).
- README with the live URL and screenshots; round out remaining backlog items.

Related: [P1 Build Plan](P1-Build-Plan.md) · [Features by Phase](../Specs/Features-by-Phase.md)
