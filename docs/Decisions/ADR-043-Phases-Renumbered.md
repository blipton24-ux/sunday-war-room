---
title: "ADR-043: Phases renumbered: model is P5, deploy and push alerts are P6"
date: 2026-11-09
tags: [adr, process, planning]
status: superseded
---
# ADR-043: Phases renumbered

> **Superseded by [ADR-049](ADR-049-Phases-Reordered-ESPN-First.md):** the phase table below is replaced. Now P3 ESPN, P4 improved model, P5 AI assistant + strategy tendencies, P6 UI/UX overhaul, P7 Yahoo, P8 deploy + push alerts ([ADR-050](ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md)). The reasoning (features before model, push alerts with deployment) still holds.

## Context
[ADR-042](ADR-042-Deploy-As-Phase-5.md) moved deployment to a final phase. The projection-model upgrades ([ADR-034](ADR-034-Ship-Model-v1-Upgrade-Later.md)) were listed inside P2, and push alerts were in P2 even though they can't be tested on a phone without a real HTTPS address.

## Options considered
| Option | Meaning |
|---|---|
| Keep upgrades in P2 | Better projections before waivers and trades; features wait on research |
| **Features first, model phase later** | Build every feature on model 1.0.0; improve the model once the features show what it needs |

## Decision
| Phase | Scope |
|---|---|
| P2 | Waivers, trade analyzer, live game day |
| P3 | AI assistant |
| P4 | ESPN + Yahoo |
| **P5** | **Improved model projections**: the ADR-034 upgrades, smarter rest-of-season projections, IDP players, dynasty/keeper (future-season) value |
| **P6** | **Deploy + push alerts** (was P5 in ADR-042) |

P2 still builds a *simple* rest-of-season projection, because waivers and trades cannot work without one; making it smart is P5. Each P5 upgrade still needs ADR-002 reuse approval and must beat the current model on held-out weeks.

## Why
Features define what the model must produce (rest-of-season values, in-game projections), and the backtest harness can measure every upgrade later. Push alerts belong with deployment because web push on a phone needs a public HTTPS address and, on iPhone, an installed app.

Related: [ADR-009 Phasing](ADR-009-Phasing.md) · [ADR-042 Deploy as a final phase](ADR-042-Deploy-As-Phase-5.md) · [Features by Phase](../Specs/Features-by-Phase.md) · [P2 Build Plan](../Build-Plan/P2-Build-Plan.md)
