---
title: "CI"
date: 2026-11-09
tags: [build-plan, ci]
---
# CI (P1 step 15)

`.github/workflows/ci.yml` runs on every push to `main` and every pull request. A newer push to the same branch cancels the older run. Four jobs; the end-to-end job waits for the first two.

| Job | Runs | Why it exists | Run it yourself |
|---|---|---|---|
| **api** | `uv lock --check`, `uv sync --frozen`, `ruff check`, `mypy` (strict), OpenAPI spec check, `pytest --cov` against Postgres + Redis from `docker compose up -d --wait db redis` | Catches style and type errors, a dependency edit without a new lock ([ADR-039](../Decisions/ADR-039-Python-Dependency-Lock-uv.md)), a stale API description, and any failing unit or integration test | `cd api` then the same commands; see `api/README.md` |
| **web** | `eslint`, `tsc`, generated-client check, Vitest | Same for the web app; the client check fails if the API changed and the TypeScript client wasn't regenerated | `cd web; npm run lint; npm run typecheck; npm run check:api; npm test` |
| **images** | Builds the api and web Docker images with layer caching | The images are what gets deployed; a Dockerfile that doesn't build should fail here, not at deploy | `docker compose build` |
| **e2e** | Builds and starts the full seeded stack, runs Playwright (Chromium), uploads the report and traces; prints container logs on failure | The only job that proves the pieces work together ([ADR-040](../Decisions/ADR-040-End-to-End-Test-Approach.md)) | `cd web; npm run e2e:up; npm run e2e` |

## Not in CI yet
- **WebKit (Safari's engine)** in the end-to-end suite: [P-14](Improvement-Backlog.md).
- **Image pinning and vulnerability scanning**: [P-09](Improvement-Backlog.md), waiting on the owner's choice of scanner.
- **Deploy**: Phase 6 adds `deploy.yml` ([ADR-042](../Decisions/ADR-042-Deploy-As-Phase-5.md)).
- First run on GitHub (2026-11-09) passed all four jobs, about 6.5 minutes end to end.
- GitHub warns that `actions/checkout@v4`, `setup-node@v4` and others still target Node 20 (forced onto Node 24); bump them when new major versions ship.

## Notes
- ESLint's `react-hooks/set-state-in-effect` rule is a warning, not an error, for seven existing effects ([P-16](Improvement-Backlog.md)).
- uv is pinned to 0.13.7 in the workflow, matching `api/Dockerfile`.

Related: [P1 Build Plan](P1-Build-Plan.md) · [Verification Gaps](Verification-Gaps.md) · [Improvement Backlog](Improvement-Backlog.md) · [ADR-019 Testing](../Decisions/ADR-019-Testing.md)
