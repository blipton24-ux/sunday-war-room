---
title: "Open Questions"
date: 2026-11-08
tags: [spec, planning]
---
# Open Questions

Not blocking Step 1. Each is decided by the owner (explain → side-by-side → recommend → ask) and becomes a new ADR.

| # | Question | Needed by | Notes |
|---|---|---|---|
| 1 | Which container platform: Railway, Render or Fly.io? | P1 deploy | Verify current pricing, managed Postgres **pgvector** support, Redis, deploy-from-GitHub flow |
| 2 | Domain name | P1 deploy | ~$10–15/yr; needed so web + api share cookies (`ffcc.app` / `api.ffcc.app`) |
| 3 | ~~Repo license and repo name~~ | — | **Decided:** [ADR-028](../Decisions/ADR-028-Repo-Name-and-License.md) |
| 4 | ~~Email provider for magic links~~ | — | **Decided:** Resend, [ADR-029](../Decisions/ADR-029-Email-Resend.md) |
| 5 | ~~Stats storage~~ | — | **Decided:** PostgreSQL, bulk-loaded, [ADR-030](../Decisions/ADR-030-Stats-In-PostgreSQL.md) |
| 6 | Privacy policy + terms page content | Before public launch | Required for Google OAuth verification too |
| 7 | Live-score delivery: polling vs Server-Sent Events vs WebSockets | P2 spec | Originally pitched as WebSockets |
| 8 | Live scores source | P2 spec | Sleeper vs public scoreboard feed |
| 9 | News sources for RAG (licensing, coverage, athlete-id tagging) | P3 spec | Old project used ESPN's public news, tagged by athlete id |
| 10 | Embedding model/provider for RAG | P3 spec | |
| 11 | AI daily message limit value | P3 spec | Cost-driven |
| 13 | Player headshots: cache/proxy ESPN's image CDN vs another source; fallback to initials | P1 build | Mockup v3 loads ESPN headshots directly ([ADR-032](../Decisions/ADR-032-Visual-Sunday-War-Room-Style.md)) |
| 12 | ESPN cookie capture flow for a web app (old one used a desktop window) | P4 spec | Security: encrypt at rest |

Related: [Features by Phase](Features-by-Phase.md) · [ADR-022 Hosting](../Decisions/ADR-022-Hosting-Container-Platform.md) · [ADR-018 AI](../Decisions/ADR-018-AI-Agent-With-RAG.md)
