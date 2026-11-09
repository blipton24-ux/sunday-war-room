---
title: "ADR-028: Repo name and license"
date: 2026-11-08
tags: [adr, process, legal]
status: accepted
---
# ADR-028: Repo name `fantasy-football-command-center`; all rights reserved

> [!NOTE]
> The **repo name** is superseded by [ADR-033](ADR-033-Name-Sunday-War-Room.md): `sunday-war-room`. The license decision stands.

## Context
The public GitHub repo ([ADR-021](ADR-021-GitHub-CICD.md)) needs a name and a license. A public repo with no license is readable but not reusable. A free v1 may later gain a paid tier ([ADR-011](ADR-011-Monetization.md)).

## Options considered — "someone copies FFCC and launches a $5/month clone"
| | **All rights reserved** | MIT | AGPL-3.0 |
|---|---|---|---|
| Code readable on GitHub | ✅ | ✅ | ✅ |
| The paid clone is legal | ❌ | ✅ | Only if they publish their code |
| Others can fork and contribute | ⚠️ Not without permission | ✅ | ✅ |
| Can change later | ✅ Can always open up | ❌ Released MIT code stays MIT | ⚠️ Only toward more open |

Names considered: `ffcc`, `fantasy-football-command-center`, `ffcc-app`.

## Decision
- Repo name: **`fantasy-football-command-center`** (the full name, easier to find in search).
- License: **all rights reserved**. Code is public to read; reuse requires permission. Stated in the README's License section. Can be relaxed to an open license later.

## Trade-offs accepted
Outside contributions aren't invited by default.

Related: [ADR-021 GitHub CI/CD](ADR-021-GitHub-CICD.md) · [ADR-011 Monetization](ADR-011-Monetization.md)
