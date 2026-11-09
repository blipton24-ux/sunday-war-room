---
title: "ADR-022: Hosting — single container platform"
date: 2026-11-08
tags: [adr, devops, hosting]
status: accepted
---
# ADR-022: Hosting — one container platform (Railway / Render / Fly.io)

## Context
Hosting = rented computers that run the five containers 24/7 at a real web address. Deployment = putting a new version there (done by CD, [ADR-021](ADR-021-GitHub-CICD.md)). Explanation: [Hosting Options](../Concepts/Hosting-Options.md).

## Options considered — merging a fix on Sunday morning
```
1 Platform:        Actions green → platform deploys new images → live in ~2 min
2 Vercel+platform: Vercel rebuilds web; platform redeploys api/worker → two dashboards
3 AWS+Terraform:   push images to AWS → ECS rolls out containers → ~5–10 min
4 Single VPS:      SSH in → docker compose pull && up → you watch it restart
```
| | 1 **Platform** | 2 Vercel + platform | 3 AWS + Terraform | 4 VPS |
|---|---|---|---|---|
| Rough monthly cost (small)* | ~$10–30 | ~$5–25 | ~$60–120+ | ~$5–12 |
| Setup | Low | Low–medium | High | Medium |
| Upkeep | Low | Low | Medium | High |
| Prod runs the tested images | ✅ | ⚠️ frontend rebuilt by Vercel | ✅ | ✅ |
| Standard at large scale | Medium | Medium | Highest | Low |

\* Ballparks from planning, **to be verified** before the P1 deploy.

### The final choice: platform vs Vercel + platform
The owner narrowed it to these two. The deciding difference is **Docker image parity**: on a single platform, the exact frontend image tested in CI is what users get. Vercel rebuilds the frontend itself and runs it as serverless/edge functions, which brings time limits, edge-runtime restrictions and config drift, so "works on my machine, breaks on Vercel" bugs can slip past CI. Vercel's advantages (global CDN, best preview URLs) didn't outweigh running two platforms. It may also need a paid plan once a paid tier exists (to verify). Full explainer: [Hosting Options](../Concepts/Hosting-Options.md#same-docker-image-as-dev).

## Decision
All five services on **one container platform** with **managed PostgreSQL and Redis**. Production runs exactly the CI-tested images.

## Open sub-question
Which platform (Railway, Render or Fly.io). Verify current pricing and **pgvector support** on its managed Postgres before the P1 deploy. Tracked in [Open Questions](../Specs/Open-Questions.md).

## Possible future phase
Migrate to **AWS + Terraform** (infrastructure-as-code) using the same images.

Related: [Hosting Options](../Concepts/Hosting-Options.md) · [ADR-020 Docker](ADR-020-Docker-Compose.md) · [ADR-021 CI/CD](ADR-021-GitHub-CICD.md)
