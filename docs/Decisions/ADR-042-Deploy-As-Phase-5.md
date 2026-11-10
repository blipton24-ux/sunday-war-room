---
title: "ADR-042: Deploy becomes Phase 5"
date: 2026-11-09
tags: [adr, process, planning, hosting]
status: accepted
---
# ADR-042: Deployment moves to Phase 5, after the app is feature-complete

> **Renumbered by [ADR-043](ADR-043-Phases-Renumbered.md):** deployment (with push alerts) is now Phase 6; Phase 5 is improved model projections.

## Context
[ADR-009](ADR-009-Phasing.md) had every phase ship deployed, and P1's step 16 was the first deploy. Hosting is billed for running containers, not for visitors, so a live but unused app costs about the same as a busy one (rough ballparks: $5–12 a month for one small server, $20–62 for a managed platform; unverified, check each provider's pricing page before deploying). Nobody but the owner would use P1 on its own, so the cost would start long before there is a reason to pay it.

## Options considered
| Option | Meaning |
|---|---|
| Deploy P1 now | Live URL early; paying for hosting through P2–P4 |
| Free tiers | Free, but sleeping web services, a database that expires and an unreliable worker |
| **Deploy in a final Phase 5** | Build P1–P4 locally with CI; deploy once, when the app is complete |

## Decision
**Deployment is Phase 5**, after P1–P4. P1's step 16 (deploy) moves there. Step 17 (docs) stays in P1 and covers everything except the live URL. Until then:
- Everything runs with `docker compose up` locally, and CI ([CI](../Build-Plan/CI.md)) runs on every push to GitHub, which is free for a public repository.
- The hosting-platform choice ([ADR-022](ADR-022-Hosting-Container-Platform.md), Open Questions #1) and domain (#2) wait until P5 and get re-checked against current prices then. ADR-022's "one platform with managed services" is not yet reconsidered; a single small server running the same images is an option to weigh again in P5.
- ADR-009's "each phase ships deployed" is amended: each phase ships **working, tested and passing CI**; P5 puts the finished app live.

## Consequences
- **Things that need a public address wait for P5:** Google OAuth production credentials and a real Resend sending domain (sign-in by Google works locally with a localhost redirect; magic links work locally), the sign-in rate limit behind a real proxy ([P-13](../Build-Plan/Improvement-Backlog.md)), and installing the app on a real phone from a real URL ([V-18](../Build-Plan/Verification-Gaps.md), [P-07](../Build-Plan/Improvement-Backlog.md)).
- **P2's web push alerts** need HTTPS and a real device to test fully. Desktop browsers accept localhost; phones need a temporary HTTPS tunnel, or the test waits for P5.
- **Deploy-time problems surface late** (production settings, image behavior on another processor, restart recovery: V-23 to V-27). Mitigation: CI already builds the images from a clean runner and runs the full stack end to end; P5 starts with a staging deploy.
- Cost starts in P5, not before.

Related: [ADR-009 Phasing](ADR-009-Phasing.md) · [ADR-022 Hosting](ADR-022-Hosting-Container-Platform.md) · [ADR-026 Execution order](ADR-026-Execution-Order.md) · [P1 Build Plan](../Build-Plan/P1-Build-Plan.md) · [P2–P4 Outline](../Build-Plan/P2-P4-Outline.md)
