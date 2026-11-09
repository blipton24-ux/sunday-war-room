# Sunday War Room

A public, installable web app (PWA) that connects to your fantasy football
leagues and helps you make weekly decisions: start/sit, matchup outlook,
waivers, trades, a live game-day dashboard, and an AI assistant that answers
questions using your league's real data and Sunday War Room's own projection model.

> **Status:** design complete, Phase 1 build not started. All decisions and
> specs live in the [docs vault](docs/README.md).

## Stack at a glance

| Layer | Choice |
|---|---|
| Frontend | Next.js + React + TypeScript, Tailwind CSS + shadcn/ui, PWA |
| Backend | Python FastAPI (API server + background worker) |
| API | REST + OpenAPI, generated TypeScript client |
| Data | PostgreSQL (+ pgvector), Redis job queue (ARQ) |
| Auth | Better Auth — Google sign-in + email magic links |
| AI | Claude tool-using agent + news retrieval (RAG) |
| Quality | pytest, Vitest, Playwright, GitHub Actions CI/CD |
| Ops | Docker + Compose, deployed to a container platform |

Every choice has a written decision record explaining the options and
trade-offs: see [docs/Decisions](docs/Decisions/INDEX.md).

## License

Copyright © 2026. **All rights reserved.** The source is public to read; it
may not be copied, modified or redistributed without permission. See
[ADR-028](docs/Decisions/ADR-028-Repo-Name-and-License.md).
