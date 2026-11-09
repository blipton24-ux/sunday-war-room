---
title: "Testing levels — unit, integration, end-to-end"
date: 2026-11-08
tags: [concept, testing]
---
# Testing levels

Tests are small programs that run your code and confirm the result is what you expect. When a later change breaks something, a test fails **before** users see it.

| Level | Checks | Sunday War Room example | Tool |
|---|---|---|---|
| **Unit** | One function alone | Projection math gives 22.4 for this stat line | pytest, Vitest |
| **Integration** | Pieces together | `GET /matchup` returns the right teams from a real test DB | pytest + test PostgreSQL |
| **End-to-end (E2E)** | A real browser clicking through | Sign in → connect Sleeper → see Week 10 matchup | Playwright |

## The testing pyramid
Many **unit** tests (fast, cheap), some **integration** tests, a few **E2E** tests (slow, but they catch the most realistic bugs).

## Sunday War Room specifics
- **Fixtures:** recorded Sleeper/nflverse responses saved in the repo, so tests never call real APIs and always give the same result.
- **Tenant isolation test:** for every user-owned endpoint, user B gets 403/404 for user A's data.
- **Model checks:** calibration (an 80% range really contains ~80% of outcomes on held-out weeks) runs as a test.
- **Regression pins:** when a bug is fixed, a test reproducing it is added so it can't come back.

Related: [ADR-019](../Decisions/ADR-019-Testing.md) · [CI/CD](CI-CD-GitHub-Actions.md)
