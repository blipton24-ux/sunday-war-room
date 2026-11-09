---
title: "Multi-tenancy"
date: 2026-11-08
tags: [concept, architecture, security]
---
# Multi-tenancy

**Multi-tenant** = one running app and one database serve many users ("tenants"), and each sees only their own data. Like an apartment building: shared building, separate locked units.

## How Sunday War Room enforces it
1. Every user-owned row links back to a `user_id` (directly, or through a league connection the user owns).
2. FastAPI gets the `user_id` **from the verified token**, never from anything the browser claims ([Auth](Auth-OAuth-Tokens.md)).
3. Every query for user-owned data is filtered by that `user_id`, through one shared helper (e.g. `get_owned_league(user, league_id)`), so no endpoint can forget.
4. Asking for someone else's league returns **404** (not 403), so the API doesn't even confirm it exists.
5. A test per endpoint proves user B can't read user A's data ([Testing Levels](Testing-Levels.md)).

## Shared vs per-user data
Some data is **shared** by everyone and stored once: NFL players, weekly stats, base projections. Other data is **per-user**: accounts, connected leagues, chat history. A league's projections depend on its scoring rules, so they're stored per scoring setup and shared by every user in that same league.

Related: [ADR-005](../Decisions/ADR-005-Public-Multi-Tenant.md) · [Data Model](../Specs/Data-Model.md) · [Auth](Auth-OAuth-Tokens.md)
