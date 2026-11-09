---
title: "ADR-005: Public product, multi-tenant"
date: 2026-11-08
tags: [adr, product, architecture]
status: accepted
---
# ADR-005: Anyone can sign up (public, multi-tenant)

## Context
Who is Sunday War Room for? This decides whether it needs accounts, data isolation, abuse protection and real hosting.

## Options considered
| Option | Upside | Downside |
|---|---|---|
| Just me | Simplest | Stays a personal tool |
| Me + league mates (10–20 users) | Accounts and deployment, manageable scope | Not a "product" |
| **Anyone (public product)** | A real product anyone can use | Scaling, abuse protection, privacy policy, running costs |

## Decision
Public product. Anyone can sign up and connect their own leagues.

## Consequences
- **Multi-tenancy**: every user's data is isolated. Every row is owned by a `user_id`, and the API checks ownership on every request. See [Multi-Tenancy](../Concepts/Multi-Tenancy.md).
- Needs real auth ([ADR-017](ADR-017-Auth-AuthJS.md)), hosting ([ADR-022](ADR-022-Hosting-Container-Platform.md)) and cost controls (rate limits, the AI daily message cap in [ADR-018](ADR-018-AI-Agent-With-RAG.md)).
- Needs a privacy policy and terms page before public launch (tracked in [Open Questions](../Specs/Open-Questions.md)).

Related: [Multi-Tenancy](../Concepts/Multi-Tenancy.md) · [ADR-017 Auth](ADR-017-Auth-AuthJS.md)
