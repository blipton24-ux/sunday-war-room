---
title: "Hosting options and Docker-image parity"
date: 2026-11-08
tags: [concept, devops, hosting]
---
# Hosting options

**Hosting** = rented computers in a data center that run your containers 24/7 at a real address (like `ffcc.app`). **Deployment** = putting a new version there.

Monthly costs: compute (web, api, worker) + **managed** PostgreSQL and Redis (the host runs, backs up and patches them) + a domain (~$10–15/yr) + Claude API usage (capped per user).

## The four options
| | Container platform (Railway/Render/Fly.io) | Vercel + platform | AWS + Terraform | Single VPS |
|---|---|---|---|---|
| What it is | Point it at your images; it runs them with managed DBs | Vercel (makers of Next.js) hosts the frontend; a platform runs the rest | ECS Fargate (containers), RDS (Postgres), ElastiCache (Redis), defined as **Terraform** code | One rented Linux machine running `docker compose up` |
| Rough cost (small)* | ~$10–30/mo | ~$5–25/mo | ~$60–120+/mo | ~$5–12/mo |
| Setup | Low | Low–medium | High | Medium |
| Upkeep | Low | Low | Medium | High: you're the sysadmin |

\* Planning ballparks; verify before deploying.

## Same Docker image as dev
An image is a frozen snapshot ([Docker](Docker-and-Compose.md)). "Same image as dev" means **the exact box tested on your laptop and in CI is the box running for real users.**

```
Just a platform:
  laptop: docker compose up → web image (Node 22, Next.js, your code)
  CI:     builds that image → Playwright tests run against it ✅
  prod:   runs THAT SAME image as an always-on Node server

Vercel + platform:
  laptop + CI: same as above ✅
  prod:   Vercel ignores your image, rebuilds from source with ITS build system,
          splits the app into serverless functions + CDN files
```
On Vercel the frontend users get is a **different build running a different way** from the one your tests checked:
- **Serverless limits:** short-lived functions with time limits, no memory between requests, possible "cold starts."
- **Edge runtime quirks:** some Next.js pieces (e.g. login-checking middleware) run on an edge runtime with only part of Node's features.
- **Version/config drift:** Node version, environment variables and build settings live in Vercel's dashboard, not your Dockerfile.

The result is occasional "works on my machine, breaks on Vercel" bugs that CI can't catch. In return, Vercel offers worldwide speed, best-in-class PR preview URLs and zero config. Its free Hobby plan is believed to be non-commercial-only (to verify).

**For Sunday War Room** the heavy logic is on the backend either way, so the difference is moderate. One platform won: one place to deploy and debug, and tests check exactly what users get ([ADR-022](../Decisions/ADR-022-Hosting-Container-Platform.md)).

## Infrastructure as code (for the possible AWS phase)
**Terraform** describes servers, networks and databases as code files, so infrastructure is created by running a script, reviewed in PRs and reproducible.

Related: [ADR-022](../Decisions/ADR-022-Hosting-Container-Platform.md) · [Docker and Compose](Docker-and-Compose.md) · [CI/CD](CI-CD-GitHub-Actions.md)
