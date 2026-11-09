---
title: "REST vs GraphQL"
date: 2026-11-08
tags: [concept, api]
---
# REST vs GraphQL

Both are ways for the frontend to ask the backend for data. They differ in **who decides what data comes back**.

- **REST: the backend decides.** A menu of fixed URLs, one per kind of data, each always returning the same shape. *Like set combo meals: order "#3" and you get the burger, fries and drink every time.*
- **GraphQL: the frontend decides.** One URL and a catalog (schema) of everything that can be asked for. Each request lists exactly the fields it wants. *Like a buffet: fill the plate with exactly what you want, but someone has to set up and maintain the buffet.*

| | REST | GraphQL |
|---|---|---|
| URLs | Many (`/leagues/123`, `/players/45`) | One (`/graphql`) |
| Who shapes the response | Backend | Frontend, per request |
| Extra or missing data | Can over-fetch, or need two calls | Exactly what's asked, one call |
| Setup in FastAPI | Built in | Extra library + schema + resolvers |
| Caching | Easy: same URL = same answer | Harder: special client caching |
| Debugging | Read the URL | Read the query text |
| Best when | One frontend, one backend | Many different client apps |

## Side by side: the Week 10 matchup screen
The screen shows both teams' starters: name, position, projected points.

**1. Backend (Python)**
```python
# REST (FastAPI): one function per URL
@app.get("/api/v1/leagues/{league_id}/matchup")
def get_matchup(league_id: int, week: int) -> Matchup:
    return matchup_service.build(league_id, week)
```
```python
# GraphQL (Strawberry): a schema of types + a resolver per field
@strawberry.type
class Query:
    @strawberry.field
    def matchup(self, league_id: int, week: int) -> Matchup:
        return matchup_service.build(league_id, week)
schema = strawberry.Schema(query=Query)
```

**2. Frontend (TypeScript)**
```ts
// REST: call a generated function
const matchup = await api.getMatchup({ leagueId: 123, week: 10 });
```
```ts
// GraphQL: write the query
const MATCHUP = gql`query { matchup(leagueId: 123, week: 10) {
  home { starters { name position projection } } } }`;
```

**3. What travels over the wire**
- REST `GET /api/v1/leagues/123/matchup?week=10` returns the full `Matchup`, including fields this screen ignores (injury status, season stats).
- GraphQL `POST /graphql` returns only the three requested fields.

**4. Needs change: a small phone widget with only names and projections**
- REST: reuse the endpoint (a bit of extra data) or add a slimmer one.
- GraphQL: write a smaller query; no backend change. *This is GraphQL's real strength.*

**5. Something breaks: the backend renames `projection` → `projected_points`**
- REST + OpenAPI: regenerate the client and TypeScript flags every usage.
- GraphQL: regenerate types from the schema; same kind of errors. Both are type-safe when set up properly.

## Sunday War Room's choice
REST + OpenAPI ([ADR-014](../Decisions/ADR-014-API-REST-OpenAPI.md)). GraphQL's flexibility pays off with many client apps, and Sunday War Room has one.

Related: [OpenAPI Typed Client](OpenAPI-Typed-Client.md) · [API spec](../Specs/API.md) · [Backend Basics](Backend-Basics.md)
