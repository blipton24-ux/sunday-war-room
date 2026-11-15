---
title: "Sunday War Room Home"
date: 2026-11-08
tags: [index, home]
aliases: [Home, 00 Home]
---
# Sunday War Room · Home

The source of truth for every decision, spec and explanation behind Sunday War Room. No code lives here. Start with the Product Vision, then skim the Decisions.

**Status (2026-11-10):** 53 decisions made; Phases 1 and 2 built and passing CI on GitHub (260 backend, 73 web, 81 end-to-end tests): P2 adds waivers, trades and live game day ([P2 Build Plan](Build-Plan/P2-Build-Plan.md)). Next is P3 ESPN ([P3 Build Plan](Build-Plan/P3-Build-Plan.md)), then P4 improved model, P5 AI assistant + strategy tendencies, P6 UI/UX overhaul, P7 Yahoo, P8 deploy + push alerts ([ADR-049](Decisions/ADR-049-Phases-Reordered-ESPN-First.md), [ADR-050](Decisions/ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md)) ([ADR-026](Decisions/ADR-026-Execution-Order.md)).

## Start here
- [Product Vision](Specs/Product-Vision.md): what Sunday War Room is, who it's for, its principles
- [Features by Phase](Specs/Features-by-Phase.md): P1–P8 scope
- [Architecture](Specs/Architecture.md): the five services and how a request flows

## Sections
- [Decisions](Decisions/INDEX.md): 53 ADRs, one per choice, with options and trade-offs
- [Concepts](Concepts/INDEX.md): plain-language explainers for every technology used
- [Specs](Specs/INDEX.md): vision, features, architecture, data model, API, UI, projection model, non-goals, open questions
- [Build Plan](Build-Plan/INDEX.md): P1 step-by-step build, [CI](Build-Plan/CI.md), verification checklist; P2 and P3 build plans; later-phases outline (P3–P8); [Improvement Backlog](Build-Plan/Improvement-Backlog.md) of things to improve later
- [Lessons from Old Projects](Lessons-from-Old-Projects.md): what the earlier fantasy apps taught, and what Sunday War Room does differently

## Stack in one table
| Layer | Choice | ADR |
|---|---|---|
| Frontend | Next.js + React + TypeScript, Tailwind + shadcn/ui, PWA | [012](Decisions/ADR-012-Frontend-NextJS.md), [010](Decisions/ADR-010-PWA.md) |
| Backend | Python FastAPI (API server + ARQ worker) | [013](Decisions/ADR-013-Backend-FastAPI.md) |
| API | REST `/api/v1` + OpenAPI-generated TS client | [014](Decisions/ADR-014-API-REST-OpenAPI.md) |
| Database | PostgreSQL + pgvector, SQLAlchemy, Alembic | [015](Decisions/ADR-015-Database-PostgreSQL.md) |
| Ingestion | Redis job queue (ARQ), scheduled + on-demand | [016](Decisions/ADR-016-Ingestion-Job-Queue.md) |
| Auth | Better Auth: Google + magic links; API reached through the web server | [035](Decisions/ADR-035-Auth-Better-Auth.md), [036](Decisions/ADR-036-API-Access-Through-Web-Server.md) |
| AI (P5) | Claude tool-using agent + news RAG | [018](Decisions/ADR-018-AI-Agent-With-RAG.md) |
| Quality | pytest, Vitest, Playwright | [019](Decisions/ADR-019-Testing.md) |
| Ops | Docker Compose, GitHub Actions CI/CD, container platform | [020](Decisions/ADR-020-Docker-Compose.md), [021](Decisions/ADR-021-GitHub-CICD.md), [022](Decisions/ADR-022-Hosting-Container-Platform.md) |
| Design | Sunday War Room style (flat, player photos), dark-first, bottom tabs | [032](Decisions/ADR-032-Visual-Sunday-War-Room-Style.md), [024](Decisions/ADR-024-Theme-Dark-First.md), [025](Decisions/ADR-025-Navigation-Bottom-Tabs.md) |

## How decisions get made
The owner makes every decision. For each one: plain-language explanation → concrete side-by-side using the same Sunday War Room example → comparison table → recommendation → owner chooses → recorded as an ADR ([ADR-003](Decisions/ADR-003-Documentation-Standard.md)). Unresolved items: [Open Questions](Specs/Open-Questions.md).
