---
title: "ADR-009: Sleeper-first MVP, then expand"
date: 2026-11-08
tags: [adr, process, planning]
status: accepted
---
# ADR-009: Phasing — Sleeper-first MVP, then expand

## Options considered
| Option | Meaning |
|---|---|
| **Sleeper-first MVP, then expand** | Each phase ships a working, deployed app |
| Feature-first, platforms later | Every feature on Sleeper, then ESPN/Yahoo at the end |
| Platform-first | All three platforms syncing before any feature: nothing to show for a while |
| Everything at once | Highest risk; nothing works until everything works |

## Decision
| Phase | Scope |
|---|---|
| **P1** | Sleeper adapter + adapter interface + accounts + start/sit + matchup + own model, **deployed live** with CI/CD |
| **P2** | Waivers + trade analyzer + live game-day dashboard (+ push alerts) |
| **P3** | AI assistant chat (agent + news RAG) |
| **P4** | ESPN + Yahoo adapters |

> **Amended by [ADR-042](ADR-042-Deploy-As-Phase-5.md):** phases ship working and passing CI; deployment is a final phase (Phase 8 since [ADR-050](ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md)).
>
> **Reordered by [ADR-049](ADR-049-Phases-Reordered-ESPN-First.md) and [ADR-050](ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md):** P3 ESPN, P4 improved model, P5 AI assistant + strategy tendencies, P6 UI/UX overhaul, P7 Yahoo, P8 deploy + push alerts.

## Why
Shipping a deployed P1 early proves the whole pipeline (code → tests → container → live URL). Every later phase is just more features on a working base.

Related: [Features by Phase](../Specs/Features-by-Phase.md) · [ADR-026 Execution order](ADR-026-Execution-Order.md) · [P1 Build Plan](../Build-Plan/P1-Build-Plan.md)
