---
title: "P1 Build Plan"
date: 2026-11-08
tags: [build-plan, p1]
---
# Phase 1 Build Plan — Sleeper MVP, deployed

Built in one go after the owner approves the vault ([ADR-026](../Decisions/ADR-026-Execution-Order.md)). Scope: [Features by Phase § P1](../Specs/Features-by-Phase.md#p1--sleeper-mvp-deployed).

## Before starting (owner decisions)
Open questions #3–5 are decided ([ADR-028](../Decisions/ADR-028-Repo-Name-and-License.md), [ADR-029](../Decisions/ADR-029-Email-Resend.md), [ADR-030](../Decisions/ADR-030-Stats-In-PostgreSQL.md)). Reuses are decided in [ADR-031](../Decisions/ADR-031-Approved-Reuses.md). #1 (platform) and #2 (domain) can wait until the deploy step.

## Repo layout
```
FFCC/
  web/                 Next.js app (TypeScript)
  api/                 FastAPI app + ARQ worker (Python), Alembic, tests
  docs/                this vault
  docker-compose.yml   web, api, worker, db, redis
  .github/workflows/   ci.yml, deploy.yml
  .env.example
```

## Build order
Each step ends with something runnable and tested.

1. **Compose stack:** Postgres (pgvector image) + Redis in `docker-compose.yml`; `.env.example`.
2. **API skeleton:** FastAPI app, config from env, `/health`, structured logging, pytest + ruff + mypy set up.
3. **Database:** SQLAlchemy models from [Data Model](../Specs/Data-Model.md), first Alembic migration, test DB fixture.
4. **Auth verification:** FastAPI dependency that verifies the web app's signed API token → `current_user`; ownership helper; tenant-isolation test pattern.
5. **Adapter interface + Sleeper adapter:** `LeagueAdapter` protocol; Sleeper implementation with recorded-fixture tests ([Adapter Pattern](../Concepts/Adapter-Pattern.md)).
6. **Worker + jobs:** ARQ settings, `sync_league` job, cron schedule, `sync_runs` tracking, job-status endpoint.
7. **nflverse source module:** `nflreadpy` loads with schema contracts (fail loudly), player id crosswalk.
8. **Projection model v1:** pure functions per [Projection Model](../Specs/Projection-Model.md): scoring with league rules, baseline, opponent, role, injury, range; unit tests; backtest script with MAE and coverage report.
9. **Services + endpoints:** matchup, lineup optimizer + swap suggestions, win-probability simulation, accuracy; all routes in [API](../Specs/API.md).
10. **OpenAPI → TS client:** generation script; CI check that it's up to date.
11. **Next.js app:** Better Auth (Google + magic link, our Postgres; [ADR-035](../Decisions/ADR-035-Auth-Better-Auth.md)), `/api/v1` pass-through to FastAPI ([ADR-036](../Decisions/ADR-036-API-Access-Through-Web-Server.md)), headshots via `next/image` ([ADR-037](../Decisions/ADR-037-Headshots-Next-Image-Cache.md)), Tailwind + shadcn theme in the Sunday War Room style ([ADR-032](../Decisions/ADR-032-Visual-Sunday-War-Room-Style.md); reference: `mockups/p1-screens-v3.html`), bottom tabs + More menu, player headshots, onboarding, Home, Matchup, Lineup, Player detail, Accuracy, Settings ([UI Screens](../Specs/UI-Screens.md)).
12. **PWA:** manifest, icons, service worker (installable).
13. **Dockerfiles:** `web`, `api` (same image runs api or worker); full `docker compose up` works.
14. **Tests:** fill gaps, starting with the open items in [Verification Gaps](Verification-Gaps.md); Playwright E2E for sign-in → connect Sleeper → matchup → lineup (real magic-link flow in E2E, no bypass; [ADR-040](../Decisions/ADR-040-End-to-End-Test-Approach.md)).
15. **CI** (done, not yet run on GitHub; see [CI](CI.md)): `ci.yml`: lint, type-check, unit, integration (Postgres + Redis services), build images, E2E.
16. **Deploy: moved to Phase 8** ([ADR-042](../Decisions/ADR-042-Deploy-As-Phase-5.md), [ADR-050](../Decisions/ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md)). Original scope kept for then: owner picks the platform ([Open Questions](../Specs/Open-Questions.md) #1); managed Postgres + Redis; `deploy.yml` on merge to main (migrate, then roll out); domain + HTTPS; Google OAuth production credentials.
17. **Docs:** update vault (any new ADRs, actual metrics), root README with screenshots (the live URL is added in P8).

## Verification checklist
- [x] `docker compose up` brings up all 5 services locally; `/health` is green on api. (verified 2026-11-09, plus the web health check)
- [x] `alembic upgrade head` runs clean on an empty database. (verified 2026-11-09 by the compose `migrate` service)
- [ ] Sign in with Google (and a magic link) works.
- [ ] Connect a real Sleeper username → leagues listed → choose team → worker syncs the league.
- [ ] Week N matchup shows projections, ranges and win probability; Lineup shows optimal lineup + swaps.
- [x] Past weeks' projections don't change on refresh (frozen). (`test_projections_freeze_at_kickoff`) [ ] Every projection shows its factors: checked in the end-to-end screens test on seeded data.
- [x] User B cannot see user A's league. (`test_tenant_isolation.py` and `e2e/isolation.spec.ts`, both in CI; no separate manual check done)
- [x] pytest, Vitest and Playwright pass locally **and** in GitHub Actions. (run 42716212296, 2026-11-09)
- [ ] (Phase 8) Merge to main auto-deploys; the same flow works on the live URL.
- [ ] PWA installs on a phone (needs a real HTTPS address, so P8); dark/light toggle works.
- [x] Backtest report committed (MAE by position, range coverage): [Backtest Report](Backtest-Report.md).

Related: [Later Phases Outline](P2-P8-Outline.md) · [Architecture](../Specs/Architecture.md) · [ADR-019 Testing](../Decisions/ADR-019-Testing.md)
