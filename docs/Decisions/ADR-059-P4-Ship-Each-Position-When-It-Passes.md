---
title: "ADR-059: P4 ships each position's settings when that position passes"
date: 2026-11-13
tags: [adr, model, process]
status: accepted
---
# ADR-059: Ship each position's settings as soon as that position passes

Amends the "after all six positions" step of the [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) round 2 ([ADR-058](ADR-058-P4-Round-2-One-Position-At-A-Time.md)).

## Context
Round 2 tunes one position at a time. The plan grouped every position's kept settings into one model version after the sixth position. RB finished first and passed on 2022-2024, 2025 and the 2026 weeks played so far; waiting for five more positions would leave a measured improvement unused for weeks of the season.

## Options considered
| Option | Result |
|---|---|
| **Ship each position when it passes** | Gains reach the app as soon as they are proven; one minor version per position (1.1.0 for RB, then 1.2.0, ...) |
| One version after all six positions | Fewer versions, but kept gains wait |

## Decision
A position's tuned settings ship as their own minor version once they pass the keep rule on 2022-2024 and 2025 **and** the one-time look at the 2026 weeks ([ADR-054](ADR-054-P4-Test-Every-Idea-One-At-A-Time.md)). The settings apply to that position only (`SHIPPED` carries them as a per-position override); every other position is unchanged. Each version refits the ranges, updates the spec and freezes past weeks under the version that computed them, as before.

## Why
Each position's settings touch only that position (the backtest shows exactly 0.000 change elsewhere), so shipping them one at a time cannot hurt another position, and the owner wanted the RB gain in the app now.

## Trade-offs accepted
More model versions on the Accuracy page. A position tuned later is compared against the shipped model, which for that position is still 1.0.0, so its numbers stay comparable.

Related: [ADR-054](ADR-054-P4-Test-Every-Idea-One-At-A-Time.md) · [ADR-055](ADR-055-P4-Keep-Rule.md) · [ADR-058](ADR-058-P4-Round-2-One-Position-At-A-Time.md) · [Model Experiments](../Build-Plan/Model-Experiments.md)
