---
title: "Databases — PostgreSQL vs SQLite vs MongoDB"
date: 2026-11-08
tags: [concept, database]
---
# Databases

A database is a program built to **store data safely, find it fast, and let many people use it at once**. Sunday War Room's backend asks the database for data and hands it to the screens. Next.js never touches it directly.

## PostgreSQL: "linked spreadsheets on a server"
Data lives in **tables**; rows point to each other with IDs:
```
users                leagues                          projections
id | email           id | name        | user_id      player      | week | points | league_id
1  | sam@...         10 | Work League | 1            J. Allen    | 10   | 22.4   | 10
                                                     B. Robinson | 10   | 17.1   | 10
```
`user_id = 1` means "this league belongs to user 1." You ask questions across tables with **SQL**:
```sql
SELECT player, points FROM projections WHERE league_id = 10 AND week = 10;
```
Runs as a separate database server. Handles many simultaneous users, **enforces rules** (a league can't point at a user who doesn't exist), and every host offers it.

## SQLite: "the same spreadsheets, in one file"
Same tables, same SQL, but stored as one file (`ffcc.db`) with no server. That's what the old projects used. It's great for one person on one machine, but only one write happens at a time, and cloud hosts can wipe the file on redeploy.

## MongoDB: "folders of JSON documents"
No tables; each record is a self-contained, nestable document:
```json
{ "_id": 10, "name": "Work League", "owner": "sam@...",
  "teams": [ { "name": "Sam's Team",
               "roster": [ { "player": "J. Allen", "week10_projection": 22.4 } ] } ] }
```
Flexible, but the same player's projection gets copied into many leagues' documents and can drift out of sync. "Every league where J. Allen is rostered" is clumsy, and rules aren't enforced.

## Side by side
| | PostgreSQL | SQLite | MongoDB |
|---|---|---|---|
| Data shape | Linked tables | Linked tables | Nested documents |
| Where it lives | Server | One file | Server |
| Many users at once | ✅ | ⚠️ | ✅ |
| Keeps data consistent | ✅ | ✅ | ⚠️ |
| Cloud hosting | ✅ | ⚠️ | ✅ |
| Fits Sunday War Room's linked data | ✅ | ✅ | ⚠️ |
| Hosting support | Widest | Limited | Wide |

## pgvector
A PostgreSQL extension that stores **embeddings** (lists of numbers representing meaning) and finds the most similar ones. Sunday War Room uses it for news search in P5 ([LLM Agents and RAG](LLM-Agents-and-RAG.md)), so there's no separate vector database.

Related: [ADR-015](../Decisions/ADR-015-Database-PostgreSQL.md) · [SQLAlchemy and Alembic](SQLAlchemy-and-Alembic.md) · [Data Model](../Specs/Data-Model.md)
