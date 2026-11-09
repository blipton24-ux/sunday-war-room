---
title: "CI/CD and GitHub Actions"
date: 2026-11-08
tags: [concept, devops, ci-cd]
---
# CI/CD and GitHub Actions

- **CI (continuous integration):** every push to GitHub triggers a robot that runs **linters** (style and bug-pattern checks), **type checks** and **tests**. You see ✅ or ❌ on the change.
- **CD (continuous deployment):** when a change passes and is merged to `main`, the robot **deploys** it to the live site.
- **GitHub Actions:** GitHub's built-in robot (free for public repos). Steps are described in YAML files under `.github/workflows/`.

## Sunday War Room's pipeline
```
push / pull request
  → lint (ruff, eslint) → type-check (mypy, tsc)
  → unit + integration tests (pytest w/ Postgres service, Vitest)
  → build Docker images → Playwright E2E against them
merge to main (all green)
  → push images → alembic upgrade head → deploy to the host
```

## Branches and pull requests
Work happens on a **branch**. A **pull request** (PR) proposes merging it into `main`, where CI runs and the change can be reviewed. `main` is protected: it only accepts changes with green checks.

## Secrets
API keys and passwords never go in the repo. They live in GitHub Actions secrets and the host's environment settings. `.env.example` lists the names with no values.

Related: [ADR-021](../Decisions/ADR-021-GitHub-CICD.md) · [Testing Levels](Testing-Levels.md) · [Docker](Docker-and-Compose.md)
