---
title: "Product Vision"
date: 2026-11-08
tags: [spec, product]
---
# Product Vision

## One line
**Sunday War Room is the Sunday command center for fantasy football managers:** connect your leagues once, and get clear, explainable start/sit calls, matchup odds, pickups, trades, live game-day tracking and an assistant that answers with your real data.

## Who it's for
Any fantasy football player on Sleeper (P1), then ESPN (P3) and Yahoo (P7) ([ADR-005](../Decisions/ADR-005-Public-Multi-Tenant.md), [ADR-006](../Decisions/ADR-006-Platform-Adapters.md)). The owner is user #1 and uses it every week.

## Principles
1. **Explain every number.** A projection shows its factors (recent form, opponent, injury, role) and a range, never a black box.
2. **Honest accuracy.** Projections freeze at kickoff and are graded only on what was actually predicted before the game.
3. **Read-only.** Sunday War Room never makes roster moves or trades on a platform ([Non-Goals](Non-Goals.md)).
4. **Fast on a phone on Sunday.** Mobile-first PWA, the Sunday War Room UI, data served from our own database.
5. **Built like a real product.** Tested, containerized, CI/CD, deployed, multi-tenant.

## Success looks like
- P1: the owner sets their real lineup from Sunday War Room on a live URL.
- The repo shows green CI, meaningful tests, automatic deploys and published accuracy numbers.

Related: [Features by Phase](Features-by-Phase.md) · [ADR-007 Features](../Decisions/ADR-007-Feature-Set.md) · [Non-Goals](Non-Goals.md)
