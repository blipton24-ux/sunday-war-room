---
title: "ADR-020: Docker + Compose everywhere"
date: 2026-11-08
tags: [adr, devops, containers]
status: accepted
---
# ADR-020: Containers — Docker + Docker Compose everywhere

## Context
Sunday War Room has five running pieces: web, api, worker, db, redis. Installing and starting each by hand on every machine is painful and error-prone. Explanation: [Docker and Compose](../Concepts/Docker-and-Compose.md).

## Options considered
| Option | Upside | Downside |
|---|---|---|
| **Docker + Compose everywhere** | `docker compose up` starts all five; same images in CI and production | Learning Docker |
| Docker only for Postgres/Redis | Simpler day to day | Dev and prod drift apart |
| No Docker | Nothing new to learn | Painful with five pieces; no reproducible environment |

## Decision
Every piece has a container. `docker-compose.yml` runs the whole stack locally:
```
docker compose up
  ├─ web      (Next.js)                 localhost:3000
  ├─ api      (FastAPI)                 localhost:8000
  ├─ worker   (ARQ jobs)
  ├─ db       (PostgreSQL + pgvector)
  └─ redis
```
The images built in CI are the exact images deployed ([ADR-022](ADR-022-Hosting-Container-Platform.md)).

Related: [Docker and Compose](../Concepts/Docker-and-Compose.md) · [ADR-022 Hosting](ADR-022-Hosting-Container-Platform.md) · [Architecture](../Specs/Architecture.md)
