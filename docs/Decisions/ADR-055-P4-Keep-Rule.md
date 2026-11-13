---
title: "ADR-055: The keep rule for model ideas"
date: 2026-11-12
tags: [adr, model]
status: accepted (amended by ADR-058)
---
# ADR-055: What an idea must prove to be kept

## Context
[ADR-054](ADR-054-P4-Test-Every-Idea-One-At-A-Time.md) tests ideas one at a time. We need one rule for "kept" so results aren't argued case by case.

## Options considered
| Option | Result |
|---|---|
| **Startable players, no position hurt** | Judges what start/sit needs; a gain at one position cannot hide a loss at another |
| Any measurable gain | Ships more, some of it noise |
| Ranking first | Closest to start/sit, but noisier to measure |

## Decision
An idea is kept only if all of these hold:
1. The average miss on **startable players** (each week's top 15 QB and TE, top 36 RB and WR) improves on the tuning seasons **and** on the check season.
2. The gain is bigger than chance (a paired bootstrap over weeks; a gain inside the noise is labelled noise and not kept).
3. No position gets worse by more than **0.05 points**.

An idea that helps one position and hurts another can be kept **for the position it helps only**. Weeks 1–4 and weeks 5+ are both reported; a gain that exists only in one is recorded as such. All numbers use the injury rule in ADR-054.

## Trade-offs accepted
Small real gains inside the noise are dropped. They stay in the ledger and can be retried with more seasons of data.

Amended by [ADR-058](ADR-058-P4-Round-2-One-Position-At-A-Time.md): kept is judged on all weeks together.

Related: [ADR-054](ADR-054-P4-Test-Every-Idea-One-At-A-Time.md) · [ADR-034](ADR-034-Ship-Model-v1-Upgrade-Later.md) · [Model Experiments](../Build-Plan/Model-Experiments.md)
