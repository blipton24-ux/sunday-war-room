---
title: "ADR-004: Engineering bar — production-grade from the start"
date: 2026-11-08
tags: [adr, process, quality]
status: accepted
---
# ADR-004: Engineering bar — production-grade from the start

## Context
Sunday War Room could be built as a quick personal tool or as a real product. Earlier fantasy tools by the same author were single-user desktop apps: never deployed, no CI, no containers.

## Options considered
| Option | Meaning |
|---|---|
| Balanced | Standard tools, moderate scope, some shortcuts |
| **Production-grade** | Built like a real product: deployed, multi-user, tested, containerized, CI/CD, even if bigger and slower to build |
| Personal tool | Usefulness to one person first; engineering practices optional |

## Decision
Production-grade. This sets the bar for later decisions: a public multi-tenant product ([ADR-005](ADR-005-Public-Multi-Tenant.md)), widely supported mainstream technology ([ADR-012](ADR-012-Frontend-NextJS.md), [ADR-015](ADR-015-Database-PostgreSQL.md)), a job queue ([ADR-016](ADR-016-Ingestion-Job-Queue.md)), and full testing and CI/CD ([ADR-019](ADR-019-Testing.md), [ADR-021](ADR-021-GitHub-CICD.md)).

## Trade-offs accepted
More to build before the first release. Balanced by **phasing** ([ADR-009](ADR-009-Phasing.md)), so a deployed, working Phase 1 ships before the larger features.

Related: [ADR-009 Phasing](ADR-009-Phasing.md) · [Product Vision](../Specs/Product-Vision.md)
