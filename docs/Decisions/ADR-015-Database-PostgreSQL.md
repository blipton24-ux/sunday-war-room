---
title: "ADR-015: Database — PostgreSQL + SQLAlchemy + Alembic"
date: 2026-11-08
tags: [adr, database, backend]
status: accepted
---
# ADR-015: Database — PostgreSQL, via SQLAlchemy, with Alembic migrations

## Context
Sunday War Room must remember users, connected leagues, rosters, stats and projections between visits, for many users at once on a cloud host. The same data shown in each option: [Databases](../Concepts/Databases.md).

## Options considered
| | **PostgreSQL** | SQLite | MongoDB |
|---|---|---|---|
| Data shape | Linked tables | Linked tables | Nested documents |
| Where it lives | Database server | One file | Database server |
| Many users at once | ✅ Built for it | ⚠️ One write at a time | ✅ |
| Keeps data consistent | ✅ Enforces rules | ✅ | ⚠️ Mostly up to your code |
| Works on cloud hosting | ✅ Every host offers it | ⚠️ File can be lost on redeploy | ✅ |
| Fits Sunday War Room's linked data | ✅ | ✅ | ⚠️ Same player copied into many documents |
| Hosting support | Widest | Limited for servers | Wide |

## Decision
- **PostgreSQL** (with the **pgvector** extension for [ADR-018](ADR-018-AI-Agent-With-RAG.md))
- **SQLAlchemy** ORM: tables as Python classes
- **Alembic** migrations: a numbered history of schema changes, applied the same way locally and in production

## Why
Sunday War Room's data is relational: users → leagues → teams → rosters → players → projections. It's a public multi-user site that must run reliably on a cloud host.

## Trade-offs accepted
More setup than a file. Solved locally by running Postgres in Docker ([ADR-020](ADR-020-Docker-Compose.md)) and in production by a managed instance ([ADR-022](ADR-022-Hosting-Container-Platform.md)).

Related: [Databases](../Concepts/Databases.md) · [SQLAlchemy and Alembic](../Concepts/SQLAlchemy-and-Alembic.md) · [Data Model](../Specs/Data-Model.md)
