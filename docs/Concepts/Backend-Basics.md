---
title: "Backend Basics — what the server side does"
date: 2026-11-08
tags: [concept, backend, python]
---
# Backend Basics

The **backend** is a program on a server that users never see. The frontend asks it for things; it answers with data.

## Sunday War Room's backend does five jobs
1. **Stores data** (users, leagues, rosters, projections) in the database.
2. **Talks to the platforms.** It calls Sleeper/ESPN/Yahoo and converts their formats into one shared format ([Adapter Pattern](Adapter-Pattern.md)).
3. **Runs the projection model** on nflverse stats.
4. **Runs background jobs** on a schedule ("Tuesday 6am: re-sync rosters, recompute projections"), separately, so users never wait ([Job Queues and Redis](Job-Queues-and-Redis.md)).
5. **Answers API requests** ("give me this week's matchup for league 123").

## The Python pieces
- **Python:** the language. Its data-science ecosystem is why Sunday War Room's backend uses it.
- **pandas:** a library for tables of data (filter, average, join), used by the model.
- **nflreadpy:** downloads nflverse NFL stats.
- **FastAPI:** a web framework. You write a normal function, and it becomes reachable at a URL:
```python
@app.get("/api/v1/leagues/{league_id}/matchup")
def get_matchup(league_id: int, week: int) -> Matchup:
    ...  # look up data, return it
```
FastAPI checks incoming data (`week` must be a number) and writes the API documentation automatically.

## How a request flows
```
You tap "Week 10 matchup" on your phone
  → Next.js page (React components, TypeScript)
  → GET /api/v1/leagues/123/matchup?week=10   (REST, via generated TS client)
  → FastAPI (Python) reads rosters + projections from PostgreSQL → returns JSON
  → React redraws the matchup table

Separately, on a schedule:
  Worker (Python) → Sleeper API + nflverse → model (pandas) → saves projections to PostgreSQL
```

## Why one codebase, two modes
The same Python code starts as the **API server** or as the **worker**. Both share adapters, model and database code, so there's no second service to keep in sync. The three backend options compared: [ADR-013](../Decisions/ADR-013-Backend-FastAPI.md).

Related: [ADR-013 Backend](../Decisions/ADR-013-Backend-FastAPI.md) · [REST vs GraphQL](REST-vs-GraphQL.md) · [Architecture](../Specs/Architecture.md)
