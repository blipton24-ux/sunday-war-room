---
title: "ADR-026: Execution order — vault first, then P1"
date: 2026-11-08
tags: [adr, process, planning]
status: accepted
---
# ADR-026: Execution order — vault first, review, then build Phase 1

## Context
The original idea was to build "in one shot" once all decisions were made. With all four phases in scope (three platforms, the model, live scores, an AI agent with RAG), building everything at once would be very large and hard to test.

## Options considered
| Option | Meaning |
|---|---|
| **Vault first, then build P1** | Write the full vault → owner reviews → build all of P1 in one go from that spec |
| Vault + P1 in one shot | No review stop in between |
| Vault only for now | Plan the P1 build in a separate session |
| Vault + all phases | The original "one shot"; very large, harder to test, delays going live |

## Decision
1. **Step 1:** create `FFCC/`, git, and the complete vault. **Stop for the owner's review.**
2. **Step 2:** build Phase 1 in one go from [P1 Build Plan](../Build-Plan/P1-Build-Plan.md).
3. Phases 2–4 each get their own plan and build ([P2–P4 Outline](../Build-Plan/P2-P8-Outline.md)).

## Why
It keeps "build from a finished spec" while letting the owner check the spec first, and gets a deployed P1 live soonest.

Related: [ADR-009 Phasing](ADR-009-Phasing.md) · [Build Plan index](../Build-Plan/INDEX.md)
