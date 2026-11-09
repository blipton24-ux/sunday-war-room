---
title: "ADR-003: Documentation standard — plain-language, example-driven"
date: 2026-11-08
tags: [adr, process, documentation]
status: accepted
---
# ADR-003: Documentation standard — plain-language and example-driven

## Context
Sunday War Room touches many technologies (Next.js, FastAPI, PostgreSQL, Redis, Docker, LLMs). Decisions are only sound if the trade-offs are understood, and docs are only useful if a newcomer can follow them.

## Options considered
| Option | Upside | Downside |
|---|---|---|
| **Plain-language + worked examples** | Anyone can follow the reasoning; trade-offs are concrete | Takes longer to write |
| Terse ADRs (decision + one-line reason) | Fast | Reasoning is lost; options look arbitrary later |
| No written decisions | Fastest | Nobody remembers *why* six months later |

## Decision
Every decision record and concept note follows the same shape:
1. A **plain-language explanation** of each option.
2. A **concrete side-by-side** that traces the *same Sunday War Room scenario* through every option (e.g. "the Week 10 matchup," "Refresh my league").
3. A **comparison table**.
4. The **choice**, why, and the trade-offs accepted.

Technology explainers live in [Concepts](../Concepts/INDEX.md), so ADRs can stay focused on the choice.

## Why
Tracing one real scenario through each option exposes differences that abstract pros/cons lists hide.

Related: [ADR-001 Vault location](ADR-001-Vault-Location.md) · [Concepts index](../Concepts/INDEX.md)
