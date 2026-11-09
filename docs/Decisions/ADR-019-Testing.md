---
title: "ADR-019: Testing — unit + integration + a few E2E"
date: 2026-11-08
tags: [adr, testing, quality]
status: accepted
---
# ADR-019: Testing — unit + integration + a few end-to-end

## Context
Tests are code that checks your code, so a change that breaks something fails *before* users see it. Explanation: [Testing Levels](../Concepts/Testing-Levels.md).

## Options considered
| Option | Meaning |
|---|---|
| **Unit + integration + a few E2E** | The standard professional mix |
| Unit + integration only | No browser tests; UI breakage caught only by hand |
| Minimal (model math only) | Risky for a public app; regressions slip through |

## Decision
| Level | Tool | Sunday War Room example |
|---|---|---|
| Unit | **pytest** (Python), **Vitest** (TS) | Projection math gives 22.4 for this stat line |
| Integration | pytest + a **real test PostgreSQL** | `GET /api/v1/leagues/{id}/matchup` returns the right teams and refuses another user's league |
| End-to-end | **Playwright** (3–5 flows) | Sign in → connect Sleeper → see Week N matchup |

Plus: a **tenant-isolation test** for every user-owned endpoint, and the model's **accuracy/calibration checks** as tests.

## Why
Many fast unit tests, some integration tests, a few slow-but-realistic E2E tests: the "testing pyramid." All run automatically in CI ([ADR-021](ADR-021-GitHub-CICD.md)).

Related: [Testing Levels](../Concepts/Testing-Levels.md) · [ADR-021 CI/CD](ADR-021-GitHub-CICD.md) · [P1 Build Plan](../Build-Plan/P1-Build-Plan.md)
