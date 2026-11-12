---
title: "ADR-057: P4 is weekly accuracy only"
date: 2026-11-12
tags: [adr, planning, model]
status: accepted
---
# ADR-057: P4 scope

## Context
The P2–P8 outline put three more things in P4 beside the weekly model: smarter rest-of-season projections, IDP (individual defensive player) support, and keeper/dynasty future value.

## Options considered
| Option | Result |
|---|---|
| **Out of P4** | P4 stays about one thing, weekly accuracy, and finishes sooner |
| End of P4, decide then | Keeps them close, but invites scope growth |
| In P4, planned now | Largest phase |

## Decision
**Out of P4.** Smarter rest-of-season (M-15), IDP (M-18) and keeper/dynasty value stay in the [Improvement Backlog](../Build-Plan/Improvement-Backlog.md) for a later phase. Rest-of-season numbers still follow the weekly model, so the backtest keeps reporting them to make sure a weekly change does not make them worse.

Related: [ADR-049](ADR-049-Phases-Reordered-ESPN-First.md) · [ADR-054](ADR-054-P4-Test-Every-Idea-One-At-A-Time.md) · [Later Phases Outline](../Build-Plan/P2-P8-Outline.md)
