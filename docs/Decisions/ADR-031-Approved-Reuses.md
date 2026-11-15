---
title: "ADR-031: Approved reuses from the earlier projects"
date: 2026-11-08
tags: [adr, process, model]
status: accepted
---
# ADR-031: Approved reuses from the earlier projects

## Context
[ADR-002](ADR-002-Fresh-Build.md) requires owner approval for each specific reuse from the earlier fantasy projects. Three candidates were listed in [Lessons from Old Projects](../Lessons-from-Old-Projects.md). "Reuse" here always means **adapt and rewrite for Sunday War Room's architecture**, never copy files in as-is.

## Decisions
| # | Candidate | Decision | When |
|---|---|---|---|
| 1 | ESPN scoring-rule mapping table (ESPN abbreviations → nflverse columns, plus the three rule shapes: per-unit, tier, range-count) | **Use the idea now; adapt the table in the ESPN phase** (P4 at the time, P3 since [ADR-049](ADR-049-Phases-Reordered-ESPN-First.md)). The Sleeper mapping is built fresh in P1 but must model all three rule shapes and treat omitted rules as zero. The ESPN table is adapted when the ESPN adapter is built. | P1 (idea), P3 (table) |
| 2 | Projection-range method: empirical quantiles of standardized residuals with an affine scale by projection, per-position floors (not clip-at-zero), volatility applied only where it persists | **Reuse the method.** Rewritten in `model/`; **all fitted numbers are refit** on Sunday War Room's own walk-forward backtest. Ships only if calibration holds (80% interval covers ~80%). | P1 |
| 3 | Grading definitions: MAE (headline), RMSE, bias, rank correlation within position-week, error by projected-points bucket, interval coverage | **Reuse the definitions.** Rewritten in Sunday War Room's code; used by both the backtest and the live accuracy page so both measure the same way. | P1 |

## Why
Each one encodes something that was learned by measurement: rules that were silently dropped, ranges that looked precise but weren't, metrics that hid the errors that matter for start/sit. Re-deriving them gains nothing. Rewriting them for Sunday War Room keeps the code consistent and fully understood.

## Not reused
Everything else: no other modules, fitted tables or configuration from the earlier projects.

Related: [ADR-002 Fresh build](ADR-002-Fresh-Build.md) · [Lessons from Old Projects](../Lessons-from-Old-Projects.md) · [Projection Model](../Specs/Projection-Model.md)
