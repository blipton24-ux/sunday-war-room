---
title: "ADR-006: ESPN + Sleeper + Yahoo behind an adapter interface"
date: 2026-11-08
tags: [adr, architecture, integrations]
status: accepted
---
# ADR-006: ESPN + Sleeper + Yahoo behind a platform adapter interface

## Context
Fantasy players use different platforms, and each exposes league data differently.

| Platform | Access |
|---|---|
| Sleeper | Free, official, public read-only API; no login needed |
| ESPN | Unofficial API; private leagues need the user's browser cookies (`espn_s2`, `SWID`) |
| Yahoo | Official API; requires OAuth ("Sign in with Yahoo") |

## Decision
Support all three, behind one **platform-agnostic adapter interface**. The rest of the app only ever sees Sunday War Room's own league/team/roster/player shapes and never a platform's raw format. See [Adapter Pattern](../Concepts/Adapter-Pattern.md).

## Why
Adding a platform becomes "write one new adapter," not "change every feature." It's the classic adapter design pattern. Sleeper goes first because it's the cleanest API ([ADR-009](ADR-009-Phasing.md)).

## Trade-offs accepted
The common model has to cover all three platforms' scoring and roster rules. Platform-specific extras get dropped or stored in a raw JSON column.

Related: [Adapter Pattern](../Concepts/Adapter-Pattern.md) · [Architecture](../Specs/Architecture.md) · [ADR-016 Ingestion](ADR-016-Ingestion-Job-Queue.md)
