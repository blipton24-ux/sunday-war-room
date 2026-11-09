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

## Why "same image everywhere" matters
CI builds the image, tests run against it, and **that exact image** is deployed. If it passed tests, production runs identical versions; only settings like the database address differ (environment variables). See [Hosting Options](Hosting-Options.md#same-docker-image-as-dev).

Related: [ADR-020](../Decisions/ADR-020-Docker-Compose.md) · [CI/CD](CI-CD-GitHub-Actions.md) · [Hosting Options](Hosting-Options.md)
