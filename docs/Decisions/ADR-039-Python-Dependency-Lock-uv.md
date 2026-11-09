---
title: "ADR-039: Python dependencies are locked with uv"
date: 2026-11-09
tags: [adr, python, docker, reproducibility]
status: accepted
---
# ADR-039: Python dependencies are locked with uv

## Context
`api/pyproject.toml` lists dependencies with lower bounds only (`fastapi>=0.115`), so every fresh install picks whatever is newest that day. The Docker images ([ADR-020](ADR-020-Docker-Compose.md)) must install exactly the versions the tests ran against, and development happens on Windows while production runs on Linux. A **lockfile** records every package and its exact version once, and everything installs from it.

**This tool choice was made while building P1 step 13** (backlog P-01 said "pick a lock tool"). It is easy to change; say so if you prefer another.

## Options considered — "a new package release breaks the Week 10 projection"
```
No lockfile:   image build tomorrow installs newest versions → may differ from what the tests ran on
pip-tools:     requirements.txt with exact versions, solved on the machine that runs it
uv:            uv.lock with exact versions, solved once for Windows AND Linux together
```
| | No lockfile | pip-tools | **uv** |
|---|---|---|---|
| Exact, repeatable installs | ❌ | ✅ | ✅ |
| One lock for Windows dev and Linux production | n/a | ❌ solved on one OS, so packages with platform rules (for example `uvloop`, Linux-only) can be missing on the other | ✅ universal lock |
| Hash-checked downloads | ❌ | ✅ (optional) | ✅ |
| Extra tools to install | none | pip-tools | uv (one binary; used inside Docker, so nobody needs it locally) |
| Install speed in CI and image builds | slow | slow | fast |

## Decision
**uv.** `api/uv.lock` is committed. The Dockerfile installs with `uv sync --frozen`, which refuses to run if the lock is out of date with `pyproject.toml`. The lock is generated in a Linux container so the result doesn't depend on the machine used:

```
cd api
docker run --rm -v "$PWD:/work" -w /work python:3.12-slim-bookworm sh -c "pip install uv==0.13.7 && uv lock"
```

Windows-only needs are expressed as platform rules inside `pyproject.toml`, not as manual steps: Windows machines get `polars[rtcompat]` (the default Polars build hangs at import on some CPUs, backlog P-03), Linux gets standard Polars.

## Why
Same versions in tests, images and production, with no surprises from a release that happened overnight, and one file that works for both operating systems.

## Trade-offs accepted
Updating a package means regenerating the lock and re-running the tests (the point). A CI check that the lock matches `pyproject.toml` comes with step 15. Developers can keep using `pip install -e ".[dev]"` locally; it just doesn't use the lock.

Related: [ADR-020 Docker](ADR-020-Docker-Compose.md) · [ADR-013 FastAPI](ADR-013-Backend-FastAPI.md) · [Docker and Compose](../Concepts/Docker-and-Compose.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md)
