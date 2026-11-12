---
title: "ADR-056: Earlier-project modelling techniques, ideas only"
date: 2026-11-12
tags: [adr, model, process]
status: accepted
---
# ADR-056: Earlier-project techniques may be tested as ideas

## Context
[ADR-002](ADR-002-Fresh-Build.md) requires approval for each reuse from the earlier fantasy projects. [ADR-034](ADR-034-Ship-Model-v1-Upgrade-Later.md) listed the techniques its model measured as useful: per-position expected-points models, depth-chart rank adjustments, defenses from betting totals, draft-capital priors, season-opener corrections and correlated simulation.

## Options considered
| Option | Result |
|---|---|
| **Ideas only, all approved to test** | Every listed technique may be tested; each is written fresh here |
| Ideas only, ask per technique | Same rule, one more question per idea |
| Port the old code | Fast, but brings the old structure and assumptions |

## Decision
Every technique listed in the vault is **approved to be tested as an idea**: written fresh in this codebase, numbers refit on our own backtest, no old code copied. This amends [ADR-031](ADR-031-Approved-Reuses.md). A technique not already listed in the vault, if it comes from the older projects, still needs its own approval.

Related: [ADR-002](ADR-002-Fresh-Build.md) · [ADR-031](ADR-031-Approved-Reuses.md) · [ADR-034](ADR-034-Ship-Model-v1-Upgrade-Later.md) · [ADR-054](ADR-054-P4-Test-Every-Idea-One-At-A-Time.md)
