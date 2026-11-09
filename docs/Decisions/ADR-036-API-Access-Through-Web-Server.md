---
title: "ADR-036: The browser reaches the API through the web server"
date: 2026-11-09
tags: [adr, auth, security, api]
status: accepted
---
# ADR-036: The browser reaches the API through the web server

## Context
Sunday War Room is two services: **web** (Next.js, draws screens, owns sign-in) and **api** (FastAPI, data and math). The API answers only requests carrying a short-lived signed token ("this is user 7, valid 15 minutes") that only the web server can create, because it holds the shared secret ([ADR-017](ADR-017-Auth-AuthJS.md), built in P1 step 4). The question is who carries that token to the API.

## Options considered — Jordan opens the Week 10 matchup
```
A Through the web server:  browser --GET /api/v1/leagues/7/matchup (session cookie)--> Next.js
                           Next.js --adds token--> FastAPI --> JSON --> Next.js --> browser
B Browser calls directly:  browser --GET /api/token (cookie)--> Next.js --> 15-minute token --> browser
                           browser --GET api.<domain>/api/v1/leagues/7/matchup + Bearer token--> FastAPI
```
| | **A: Through the web server** | B: Direct |
|---|---|---|
| Where the token lives | Only on the server | In the page's memory |
| If a malicious script ever ran on the page | No token to steal (it can still act while the page is open) | Can take the token and use it elsewhere for up to 15 minutes |
| Hosts and browser rules | One origin; no CORS | Two hosts; CORS rules and token refresh |
| Server-rendered pages | Same call path | Separate path |
| Cost | One extra hop (milliseconds) | — |

## Decision
**A.** The browser only talks to the web app's own origin:
- `/api/auth/*` is Better Auth ([ADR-035](ADR-035-Auth-Better-Auth.md)).
- `/api/v1/*` is a thin pass-through route in Next.js: it checks the session, mints the 15-minute token, forwards method, query and body to FastAPI, and returns FastAPI's status and body unchanged (including the `{detail, code}` errors).
- Server-rendered pages call FastAPI directly from the server with the same token.

FastAPI is not exposed to browsers in production; CORS is not needed.

## Why
Simplest secure option: the token never reaches browser JavaScript, there is one origin and one cookie, and every call path uses the same generated client ([ADR-014](ADR-014-API-REST-OpenAPI.md)).

## Trade-offs accepted
An extra hop per data request, and the web service must be up for data (it must be up for pages anyway). Long-running work is already asynchronous (202 + job id), so the proxy never holds a request open for long.

Related: [ADR-035 Better Auth](ADR-035-Auth-Better-Auth.md) · [ADR-017 Auth](ADR-017-Auth-AuthJS.md) · [Architecture](../Specs/Architecture.md) · [API](../Specs/API.md)
