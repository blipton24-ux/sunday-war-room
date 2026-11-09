---
title: "ADR-035: Auth library — Better Auth (supersedes ADR-017's library choice)"
date: 2026-11-09
tags: [adr, auth, security]
status: accepted
---
# ADR-035: Auth library — Better Auth (supersedes the library choice in ADR-017)

## Context
[ADR-017](ADR-017-Auth-AuthJS.md) chose Auth.js for "Sign in with Google" and email magic links, with users stored in our own PostgreSQL. Before the web app was built (P1 step 11), two facts surfaced:

- On 2025-09-22 Auth.js moved under the Better Auth team, which said it will keep "addressing security patches and urgent issues" and "strongly recommend[s] new projects to start with Better Auth" ([announcement](https://better-auth.com/blog/authjs-joins-better-auth)).
- Auth.js v5, the App Router version, is still published as `5.0.0-beta.x`; npm's `latest` tag is the older v4.

Everything else in ADR-017 stands: Google + magic links, users in our PostgreSQL, a signed token that FastAPI verifies ([ADR-036](ADR-036-API-Access-Through-Web-Server.md)), authorization by `user_id` on every query.

## Options considered — a new user signs up with Google
```
Better Auth:  "Sign in with Google" → Google → user row in OUR Postgres → session cookie → Week 10 loads
Auth.js v5:   "Sign in with Google" → Google → user row in OUR Postgres → session cookie → Week 10 loads
```
| | **Better Auth** | Auth.js v5 |
|---|---|---|
| Actively developed | ✅ | ❌ security fixes and urgent issues only |
| Stable release | ✅ | ❌ still beta |
| Google + magic links + own Postgres | ✅ (magic links via a plugin; email sent through Resend, [ADR-029](ADR-029-Email-Resend.md)) | ✅ |
| Fits our schema (integer user ids, our table names) | ✅ `generateId: "serial"`, `modelName` / `fields` mapping | ✅ already built |
| Work now | One Alembic migration reshaping the auth tables (no users yet) | None |
| Switching later | n/a | Migrating real users' accounts and sessions |

## Decision
**Better Auth**, configured for:
- **Google** sign-in and **email magic links** (Resend in production; in local development without a Resend key the link is written to the server log, never in production).
- **Our PostgreSQL**, with database-generated integer ids so `users.id` stays the integer the API already uses, and snake_case column names mapped with `fields`.
- **Alembic stays the only owner of the schema** ([ADR-015](ADR-015-Database-PostgreSQL.md)): Better Auth's CLI is used to read the schema it expects, never to change the database. Better Auth's startup check confirms the two agree.

## Why
The users see the same thing either way. The difference is the library's future: choosing a maintenance-only, still-beta library for a public app means a forced migration later, when it would involve real accounts. Today it costs one migration of empty tables.

## Trade-offs accepted
A younger library with fewer years in production. Its table shapes differ from Auth.js's, so the step-3 auth tables are replaced (they hold no data). The [Data Model](../Specs/Data-Model.md) and [Auth concept note](../Concepts/Auth-OAuth-Tokens.md) are updated to match.

Related: [ADR-017 Auth](ADR-017-Auth-AuthJS.md) · [ADR-036 API access](ADR-036-API-Access-Through-Web-Server.md) · [ADR-029 Resend](ADR-029-Email-Resend.md) · [Auth, OAuth and Tokens](../Concepts/Auth-OAuth-Tokens.md)
