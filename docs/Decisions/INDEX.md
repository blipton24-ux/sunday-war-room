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
- [ADR-009 Phasing](ADR-009-Phasing.md): P1–P4 (current order: ADR-049)
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
- [ADR-042 Deploy becomes Phase 5](ADR-042-Deploy-As-Phase-5.md): build P1–P4 locally with CI; deploy once the app is complete (amends ADR-009; hosting choice waits)
- [ADR-043 Phases renumbered](ADR-043-Phases-Renumbered.md): P5 improved model, P6 deploy + push alerts (phase table superseded by ADR-049, amended by ADR-050)
- [ADR-044 Live data sources](ADR-044-Live-Data-Sources.md): Sleeper points + ESPN public scoreboard for game state (closes open question #8)
- [ADR-045 Live delivery by polling](ADR-045-Live-Delivery-Polling.md): re-fetch every 30-60 s only while games are live (closes #7)
- [ADR-046 Any league](ADR-046-Any-League-Settings.md): every feature reads the league's waiver, roster and scoring settings
- [ADR-047 Waivers](ADR-047-Waivers-Value-Added.md): value added to my lineup, rest of season or this week, drop and FAAB bid suggestions
- [ADR-048 Trades](ADR-048-Trades-Lineup-Impact.md): lineup impact, any two teams, "best for me, still acceptable" suggestions
- [ADR-049 Phases reordered, ESPN first](ADR-049-Phases-Reordered-ESPN-First.md): P3 ESPN + Yahoo, P4 improved model, P5 AI assistant + strategy tendencies, P6 UI/UX overhaul, P7 deploy + push alerts (amended by ADR-050)
- [ADR-050 Yahoo is P7, deploy is P8](ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md): P3 ESPN only; Yahoo right before deployment
- [ADR-051 ESPN access](ADR-051-ESPN-Access-Link-First-Cookie-Fallback.md): league link first, guided cookie paste for private leagues, own cookies only (closes open question #12)
- [ADR-052 Credential encryption](ADR-052-Credential-Encryption.md): app-level Fernet key from the environment; cookies never in job args, logs or responses
- [ADR-053 ESPN client](ADR-053-ESPN-Client-Own-Code.md): our own client; approved rewrites of earlier ESPN lessons (amends ADR-031)
- [ADR-060 P4 machine-learning model](ADR-060-P4-Machine-Learning-Stats-Then-Score.md): predict each stat with XGBoost, then score with the league's rules; the first P4 approach (ADR-054..059) removed, its measuring tools kept
- [ADR-061 How the ML model is tested and shipped](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md): season-by-season walk-forward on 2022-2025, settings chosen inside training seasons, ship rule, rank accuracy and outside benchmark reported
- [ADR-062 Training history from 2016](ADR-062-P4-Training-History-From-2016.md): the ML model loads and trains on every season from 2016
- [ADR-063 Depth charts and player background tables](ADR-063-P4-Depth-Charts-And-Player-Background-Tables.md): two new tables, filled from nflverse, for the ML model and the live compute
- [ADR-064 Spread-aware scoring of predicted stats](ADR-064-P4-Spread-Aware-Scoring-Of-Predicted-Stats.md): step and bonus rules score their expected value under a learned spread (gamma)
- [ADR-065 Retrain every 4 weeks in testing](ADR-065-P4-Retrain-Every-Four-Weeks-In-Testing.md): the four-season test retrains before weeks 1, 5, 9 and 13 with the season so far added
- [ADR-066 Sleeper's projections as a local benchmark](ADR-066-P4-Sleeper-Projections-As-A-Local-Benchmark.md): fetched into a git-ignored cache, totals in reports only, never a model input
- [ADR-067 P4 scope: the best model now](ADR-067-P4-Scope-For-The-Best-Model-Now.md): every model experiment with evidence goes into P4, rest-of-season model added, second-half injuries marked
- [ADR-068 Questionable players projected as if they play](ADR-068-P4-Questionable-Players-Projected-If-Playing.md): trimmed "if he plays" number shown, fitted chance he plays beside it and in win probability
- [ADR-069 Practice status in the model, news shown only](ADR-069-P4-Practice-Status-In-The-Model-News-Shown-Only.md): the chance he plays uses the official practice report; ESPN's injury news is displayed, never a model input
- [ADR-070 Tuning run](ADR-070-P4-Tuning-Run-Grid-Targets-History.md): settings grid widened to 24, the model kept for every target, training from 2012 tested and kept only if better
- [ADR-071 Play-by-play counts only](ADR-071-P4-Play-By-Play-Counts-Only.md): play-by-play becomes per-player-week counts (goal-line, red-zone, end-zone); the plays are not stored
- [ADR-072 One model, no blend](ADR-072-P4-One-Model-No-Blend.md): 2.0.0 projects QB, RB, WR and TE with the ML model alone; 1.0.0's method retires for them
- [ADR-073 Model trainings in the database](ADR-073-P4-Model-Trainings-In-The-Database.md): every training stored in `model_trainings`; `model_version` names the method, each projection records its training
- [ADR-074 Late injuries](ADR-074-P4-Late-Injuries-ESPN-Feed-And-Sunday-Sleeper-Fetch.md): ESPN's injury feed polled near each kickoff, and Sunday's Sleeper fetch moved after inactives
- [ADR-075 Questionable starters](ADR-075-P4-Questionable-Starters-Start-If-Active-With-Fallback.md): start/sit advice says start him if active and names a fallback; chance-weighted only when the fallback locks first
- [ADR-076 Weekly retrain with a sanity gate](ADR-076-P4-Weekly-Retrain-With-A-Sanity-Gate.md): a Tuesday training goes live only if complete, not worse on its held-back season, and without sudden position shifts
- [ADR-077 Rest-of-season points over replacement](ADR-077-P4-Rest-Of-Season-Points-Over-Replacement.md): value shown over the last starter league-wide; the long-range model built only if 2.0.0 carried across still loses
- [ADR-038 Service worker scope](ADR-038-Service-Worker-Scope.md): static files and an offline page only, never API data (offline data is backlog U-11)
- [ADR-039 Python dependency lock (uv)](ADR-039-Python-Dependency-Lock-uv.md): exact, repeatable installs for Windows and Linux
- [ADR-040 End-to-end test approach](ADR-040-End-to-End-Test-Approach.md): real browser, whole container stack, recorded league plus seeded NFL data, real magic-link sign-in
- [ADR-041 Accessibility standard](ADR-041-Accessibility-Standard.md): WCAG 2.1 AA enforced by axe on every screen; palette adjustments

Up: [Home](../README.md)
