---
title: "Decisions (ADR index)"
date: 2026-11-08
tags: [index, adr]
---
# Decisions — Architecture Decision Records

One record per decision: context, options considered, the choice, why, and trade-offs. All decided by the owner on 2026-11-08.

## Product & process
- [ADR-001 Vault location](ADR-001-Vault-Location.md): why the docs live in `FFCC/docs`
- [ADR-002 Fresh build](ADR-002-Fresh-Build.md): new code; old projects are lessons only
- [ADR-003 Documentation standard](ADR-003-Documentation-Standard.md): how decisions and concepts are written up
- [ADR-004 Production-grade bar](ADR-004-Production-Grade-Bar.md): the engineering bar behind every other choice
- [ADR-005 Public, multi-tenant](ADR-005-Public-Multi-Tenant.md): anyone can sign up
- [ADR-006 Platform adapters](ADR-006-Platform-Adapters.md): Sleeper, ESPN, Yahoo behind one interface
- [ADR-007 Feature set](ADR-007-Feature-Set.md): the four feature areas
- [ADR-008 Own projection model](ADR-008-Own-Projection-Model.md): nflverse-based model
- [ADR-009 Phasing](ADR-009-Phasing.md): P1–P4
- [ADR-010 PWA](ADR-010-PWA.md): responsive web app, installable
- [ADR-011 Monetization](ADR-011-Monetization.md): free v1, payment-ready

## Technology
- [ADR-012 Frontend: Next.js](ADR-012-Frontend-NextJS.md): React + TypeScript + Tailwind
- [ADR-013 Backend: FastAPI](ADR-013-Backend-FastAPI.md): one Python codebase, API + worker
- [ADR-014 API: REST + OpenAPI](ADR-014-API-REST-OpenAPI.md): generated TS client
- [ADR-015 Database: PostgreSQL](ADR-015-Database-PostgreSQL.md): SQLAlchemy + Alembic
- [ADR-016 Ingestion: job queue](ADR-016-Ingestion-Job-Queue.md): Redis + ARQ
- [ADR-017 Auth: Auth.js](ADR-017-Auth-AuthJS.md): Google + magic links (library superseded by ADR-035)
- [ADR-018 AI: agent + RAG](ADR-018-AI-Agent-With-RAG.md): Claude, tools, pgvector news search
- [ADR-019 Testing](ADR-019-Testing.md): unit + integration + E2E
- [ADR-020 Docker + Compose](ADR-020-Docker-Compose.md): five containers
- [ADR-021 GitHub CI/CD](ADR-021-GitHub-CICD.md): public repo, Actions
- [ADR-022 Hosting](ADR-022-Hosting-Container-Platform.md): one container platform

## Design & execution
- [ADR-023 Broadcast style](ADR-023-Visual-Broadcast-Style.md): superseded by ADR-032
- [ADR-024 Dark-first theme](ADR-024-Theme-Dark-First.md): with light toggle
- [ADR-025 Bottom tabs](ADR-025-Navigation-Bottom-Tabs.md): Home · Lineup · Matchup · Chat · More
- [ADR-026 Execution order](ADR-026-Execution-Order.md): vault → review → P1
- [ADR-027 Public/private docs](ADR-027-Public-Private-Docs.md): engineering docs public, personal notes git-ignored
- [ADR-028 Repo name and license](ADR-028-Repo-Name-and-License.md): `fantasy-football-command-center`, all rights reserved
- [ADR-029 Email via Resend](ADR-029-Email-Resend.md): magic-link delivery
- [ADR-030 Stats in PostgreSQL](ADR-030-Stats-In-PostgreSQL.md): bulk-loaded nflverse history
- [ADR-031 Approved reuses](ADR-031-Approved-Reuses.md): what's adapted from the earlier projects, and when
- [ADR-032 Sunday War Room style](ADR-032-Visual-Sunday-War-Room-Style.md): flat Odyssey palette, player photos (replaces ADR-023)
- [ADR-033 Name: Sunday War Room](ADR-033-Name-Sunday-War-Room.md): app name, logo, repo `sunday-war-room`
- [ADR-034 Ship model v1, upgrade later](ADR-034-Ship-Model-v1-Upgrade-Later.md): P1 launches on model 1.0.0; upgrades after deploy, each gated on the backtest
- [ADR-035 Better Auth](ADR-035-Auth-Better-Auth.md): sign-in library (supersedes ADR-017's library choice)
- [ADR-036 API access through the web server](ADR-036-API-Access-Through-Web-Server.md): the browser never holds the API token
- [ADR-037 Headshots via the Next.js image cache](ADR-037-Headshots-Next-Image-Cache.md): resized, cached ESPN images with initials fallback (closes open question #13)
- [ADR-038 Service worker scope](ADR-038-Service-Worker-Scope.md): static files and an offline page only, never API data (offline data is backlog U-11)
- [ADR-039 Python dependency lock (uv)](ADR-039-Python-Dependency-Lock-uv.md): exact, repeatable installs for Windows and Linux

Up: [Home](../README.md)
