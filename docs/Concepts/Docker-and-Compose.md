---
title: "Docker and Docker Compose"
date: 2026-11-08
tags: [concept, devops, containers]
---
# Docker and Docker Compose

## The problem
Sunday War Room has five running pieces: Next.js, FastAPI, the worker, PostgreSQL and Redis. Installing the right version of each on every machine (yours, CI, the server) is error-prone: "it works on my machine."

## Image and container
- A **Docker image** is a **frozen snapshot** of everything one piece needs: OS layer, exact Node/Python version, every package, your built code. Once built, it never changes.
- A **container** is a running copy of an image: a sealed box that behaves the same everywhere.
- A **Dockerfile** is the recipe that builds an image.

## Docker Compose
One file (`docker-compose.yml`) lists all the boxes and how they connect, so one command starts everything:
```
docker compose up
  ├─ web      (Next.js)               localhost:3000
  ├─ api      (FastAPI)               localhost:8000
  ├─ worker   (ARQ jobs)
  ├─ db       (PostgreSQL + pgvector)
  └─ redis
```

## How Sunday War Room's images are built
- **Two images, five services.** `web` (Next.js) and `api`. The `api` image runs three jobs depending on the command it is given: the web API, the background worker, and the one-shot database migration. Same code, same versions.
- **Start order is enforced.** `db` and `redis` become healthy → `migrate` runs once and exits → `api` and `worker` start → `web` starts when `api` is healthy. A broken migration stops everything before any user-facing service runs.
- **Exact versions.** Python packages come from `api/uv.lock` ([ADR-039](../Decisions/ADR-039-Python-Dependency-Lock-uv.md)); Node packages from `web/package-lock.json`.
- **Small and unprivileged.** Multi-stage builds keep build tools out of the final image, both run as non-root users, and nothing secret is baked in: every setting is read from environment variables when the container starts.
- **First start fills itself.** A brand-new database has no NFL history, so the worker queues a full nflverse load when it starts and finds none.

## Why "same image everywhere" matters
CI builds the image, tests run against it, and **that exact image** is deployed. If it passed tests, production runs identical versions; only settings like the database address differ (environment variables). See [Hosting Options](Hosting-Options.md#same-docker-image-as-dev).

Related: [ADR-039](../Decisions/ADR-039-Python-Dependency-Lock-uv.md) · [ADR-020](../Decisions/ADR-020-Docker-Compose.md) · [CI/CD](CI-CD-GitHub-Actions.md) · [Hosting Options](Hosting-Options.md)
