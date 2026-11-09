---
title: "ADR-040: End-to-end tests run a real browser against the whole stack, with a seeded world"
date: 2026-11-09
tags: [adr, testing, playwright, docker]
status: accepted
---
# ADR-040: End-to-end tests run a real browser against the whole stack, with a seeded world

## Context
[ADR-019](ADR-019-Testing.md) calls for a few Playwright end-to-end tests ("sign in → connect Sleeper → see the matchup"), and the [Verification Gaps](../Build-Plan/Verification-Gaps.md) list needed far more screens, buttons and states looked at than that. Three questions had no answer in the vault: where the data comes from, how a test signs in, and which browser runs locally.

**These choices were made while building P1 step 14.** They are testing infrastructure, easy to change.

## Options considered — "the test opens the Lineup and checks the swap suggestion"
```
Data:   A live Sleeper + live nflverse       the league changes weekly; tests would break when the NFL week does
        B recorded league + invented NFL     same answer every run, every state of the UI can be arranged
Sign in: A a test-only login inside the app  fast, but a back door that must never ship
         B the real link flow, token read from the app's own database   slower, nothing extra in the app
```
| | A: live data / back door | **B: recorded + seeded / real flow** |
|---|---|---|
| Same result every run | ❌ | ✅ |
| Can show "a starter is on bye" on demand | ❌ (wait for a real bye) | ✅ |
| Extra code that ships in the app | a login back door | none |
| Depends on the internet | yes | no (Sleeper is replaced by a local stand-in) |

## Decision
- **The stack:** the real services (db, redis, migrate, api, worker, web) from `docker-compose.yml`, plus `docker-compose.e2e.yml`, on its own project name and ports so it never touches the development stack. `npm run e2e:up` starts it with a fresh database.
- **Sleeper** is replaced by a small local server (`web/e2e/mock_sleeper.py`) that serves the recorded, anonymized league from `api/tests/fixtures/sleeper`. The worker is pointed at it with `SLEEPER_BASE_URL`.
- **The NFL side is invented** by `api/tests/e2e_seed.py`, run once at start: games, stat lines, injuries, frozen and graded past projections, with times relative to "now". The fixture user's team has a starter on bye, one in progress, one questionable, a QB who booms, and two swaps to make, so every UI state exists. The worker's own first-run load and scheduled jobs are switched off (`INITIAL_INGEST`, `CRON_ENABLED`) so seeded data is never replaced.
- **Signing in is real:** the test types an email in the sign-in screen, then reads the one-time token the app stored in its database and opens the link. There is no test-only login. Sign-in link rate limits are raised for the test stack only (`MAGIC_LINK_RATE_LIMIT_MAX`).
- **Browsers:** locally, the Edge already installed on Windows (`PW_CHANNEL=msedge`; nothing to download and it runs under Windows Smart App Control). In CI, Playwright's own Chromium.
- **Layout (`web/e2e`):** `onboarding.setup.ts` (a new person's first visit, saves the signed-in state), `screens.spec.ts`, `accessibility.spec.ts`, `mobile.spec.ts` (iPhone-sized, touch), then the specs that change data or sign people out, each with its own throwaway user: `actions.spec.ts`, `isolation.spec.ts` (privacy between people), `pwa.spec.ts`.

## Why
Realistic enough to catch the bugs that only appear when the pieces meet (and it did: see the backlog), deterministic enough to run in CI, and nothing test-specific ships in the product.

## Trade-offs accepted
- The NFL data is synthetic, so these tests prove the screens and flows, not the accuracy of the projections (that is the backtest's job).
- The suite runs in Chromium only. Safari's engine (WebKit), which every iPhone uses, is not covered yet (backlog P-14).
- Changing the web app means rebuilding its image before the tests see it (about a minute).

Related: [ADR-019 Testing](ADR-019-Testing.md) · [ADR-020 Docker](ADR-020-Docker-Compose.md) · [Testing Levels](../Concepts/Testing-Levels.md) · [Verification Gaps](../Build-Plan/Verification-Gaps.md)
