---
title: "ADR-034: Ship projection model v1 in P1; upgrade it later"
date: 2026-11-08
tags: [adr, model, planning]
status: accepted
---
# ADR-034: Ship projection model v1 in P1; upgrade it later

## Context
Projection model v1 ([Projection Model](../Specs/Projection-Model.md)) was built and backtested in P1 step 8 ([Backtest Report](../Build-Plan/Backtest-Report.md)). It was then compared with the earlier fantasy project's model (v5), which is prior art only ([ADR-002](ADR-002-Fresh-Build.md)). That model had many measured improvements that v1 does not have: per-position models on expected fantasy points, depth-chart adjustments, draft-capital priors, defenses projected from betting totals, correlated simulation, and season-opener corrections.

Like-for-like slice: weeks 5–18, held-out season, full PPR. Average miss in points (lower is better):

| | Earlier project v5 | Sunday War Room v1 | Naive season average |
|---|---|---|---|
| All players, 2024 / 2025 | 4.40 / 4.33 | 4.46 / 4.33 | 4.44 / 4.34 |
| Startable players*, 2024 / 2025 | 5.78 / 5.83 | 6.35 / 6.45 | 6.26 / 6.50 |
| QB rank correlation (startable), 2024 / 2025 | 0.37 / 0.29 | 0.15 / 0.14 | — |

\*Each week's top 15 QB/TE and top 36 RB/WR. Not exact: the earlier project scored with its own league's rules and selected startable players by its own projections. The gap on startable players (~0.6 points per player) is larger than those differences.

## Options considered
```
A Ship v1:      finish P1 (TS client, web app, deploy) on model 1.0.0 → upgrade the model afterwards
B Upgrade now:  rewrite the best-measured techniques as model v2 → gate on the backtest → then the web app
```
| | **A: Ship v1** | B: Upgrade first |
|---|---|---|
| Time to a deployed P1 | Sooner | Later |
| Start/sit quality at launch | ≈ naive season average on startable players | Likely closer to the earlier project |
| Integrity rules (freeze, genuine grading, `model_version`) | ✅ | ✅ |
| Live graded weeks collected before the upgrade | Yes: v2 can be judged on real frozen predictions too | No |

## Decision
**A.** P1 ships with model 1.0.0. Model upgrades come after P1 is deployed, as a numbered model version.

## Why
The rest of P1 (web app, PWA, CI/CD, deploy) doesn't depend on the model's accuracy, and every integrity rule is already in place. A deployed v1 also starts building a ledger of genuine, frozen weekly predictions, which gives any v2 a live yardstick as well as the backtest.

## Trade-offs accepted
- At launch, start/sit advice on startable players is roughly as accurate as a plain season average. The Accuracy page and the backtest report state the numbers rather than hiding them.
- Upgrades follow the existing rule ([Projection Model](../Specs/Projection-Model.md) § Evaluation): a new version ships only if it beats the current one on held-out weeks without making any position notably worse. The startable-player slice above becomes part of that check.
- Reusing any specific technique from the earlier project still needs its own approval ([ADR-002](ADR-002-Fresh-Build.md)), recorded the way [ADR-031](ADR-031-Approved-Reuses.md) was. Candidates, in order of measured benefit: per-position expected-points models, depth-chart rank adjustments, defenses from betting totals, correlated simulation, draft-capital priors, season-opener corrections.

Related: [ADR-031 Approved reuses](ADR-031-Approved-Reuses.md) · [Projection Model](../Specs/Projection-Model.md) · [Backtest Report](../Build-Plan/Backtest-Report.md) · [P2–P4 Outline](../Build-Plan/P2-P4-Outline.md)
