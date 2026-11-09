---
title: "ADR-021: Public GitHub + Actions CI/CD"
date: 2026-11-08
tags: [adr, devops, ci-cd]
status: accepted
---
# ADR-021: Code hosting & CI/CD — public GitHub repo + GitHub Actions

## Context
- **CI** (continuous integration): a robot runs checks and tests on every push.
- **CD** (continuous deployment): a robot deploys every change that passes.

Explanation: [CI/CD and GitHub Actions](../Concepts/CI-CD-GitHub-Actions.md).

## Options considered
| Option | Upside | Downside |
|---|---|---|
| **Public GitHub + Actions CI/CD** | Anyone can browse the code, docs and CI status | Code is public (secrets must never be committed) |
| Private GitHub + Actions CI/CD | Hidden code | Code isn't open for others to read |
| Public, CI only (manual deploy) | Less setup | Deploys stay manual and error-prone |

## Decision
Public GitHub repo. GitHub Actions pipeline:
```
push / pull request → lint → type-check → unit + integration tests → E2E → build Docker images
merge to main (all green) → push images → run Alembic migrations → deploy
```
Secrets live only in GitHub Actions secrets and the host's environment settings, never in the repo (`.env` is git-ignored; a `.env.example` documents the names).

Related: [CI/CD and GitHub Actions](../Concepts/CI-CD-GitHub-Actions.md) · [ADR-019 Testing](ADR-019-Testing.md) · [ADR-020 Docker](ADR-020-Docker-Compose.md)
