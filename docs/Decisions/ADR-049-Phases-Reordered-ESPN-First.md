---
title: "ADR-049: Phases reordered: ESPN + Yahoo next, then model, AI + strategy, UI/UX, deploy"
date: 2026-11-10
tags: [adr, process, planning]
status: accepted
---
# ADR-049: Phases reordered, ESPN + Yahoo first

## Context
P1 (Sleeper MVP) and P2 (waivers, trades, live game day) are built. [ADR-043](ADR-043-Phases-Renumbered.md) set the remaining order as P3 AI assistant · P4 ESPN + Yahoo · P5 improved model · P6 deploy + push alerts. Until an ESPN adapter exists, every feature can only be exercised against Sleeper leagues. The owner's own league is on ESPN, which makes it the most complete real-world test case available, with a real roster, real scoring rules and a real weekly result to compare against.

## Options considered
| Option | Meaning |
|---|---|
| Keep ADR-043 order | AI assistant next; ESPN + Yahoo after it; the model and the AI are built and tested on Sleeper data only |
| **ESPN + Yahoo first** | New adapters next; the model upgrades, the AI assistant and the UI pass are all tested on a real ESPN league as they're built |

## Decision
| Phase | Scope | Was |
|---|---|---|
| **P3** | **ESPN + Yahoo adapters**: ESPN first, then Yahoo; scoring-rule coverage for each | P4 |
| **P4** | **Improved model projections**: the [ADR-034](ADR-034-Ship-Model-v1-Upgrade-Later.md) upgrades, smarter rest-of-season projections, IDP players, dynasty/keeper value | P5 |
| **P5** | **AI assistant + strategy tendencies**: the Chat tab ([ADR-018](ADR-018-AI-Agent-With-RAG.md)), plus a manager's strategy tendencies shown as badges and nudges (new scope) | P3, plus new scope |
| **P6** | **UI/UX overhaul**: a full design pass over every screen so the app presents everything P1–P5 added coherently (new) | none |
| **P7** | **Deploy + push alerts**, then round out | P6 |

Strategy tendencies is new scope: what it measures, where it shows and any reuse from earlier projects ([ADR-002](ADR-002-Fresh-Build.md)) are decided in the P5 plan. The UI/UX scope is decided in the P6 plan. Everything else in ADR-043 still holds: each model upgrade needs ADR-002 reuse approval and must beat the current model on held-out weeks, and deployment stays last ([ADR-042](ADR-042-Deploy-As-Phase-5.md)).

## Why
- **Real data early.** ESPN scoring rules, roster formats and cookie-based access are the least-known parts of the system. Building them first exposes adapter gaps before more features depend on them, and puts the [adapter pattern](../Concepts/Adapter-Pattern.md) under real load.
- **Model before AI.** The assistant's answers are only as good as the projections its tools return, so the improved model comes first.
- **UI after features.** A single design pass once all features exist avoids redesigning screens twice.
- **Deploy last** keeps hosting cost at zero until the app is complete (ADR-042).

Supersedes the phase table in [ADR-043](ADR-043-Phases-Renumbered.md). **Amended by [ADR-050](ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md):** Yahoo moved out of P3 into its own P7, and deploy + push alerts became P8.

Related: [ADR-009 Phasing](ADR-009-Phasing.md) · [ADR-043 Phases renumbered](ADR-043-Phases-Renumbered.md) · [Features by Phase](../Specs/Features-by-Phase.md) · [Later Phases Outline](../Build-Plan/P2-P8-Outline.md)
