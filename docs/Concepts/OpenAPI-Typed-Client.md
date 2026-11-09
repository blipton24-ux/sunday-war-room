---
title: "OpenAPI and the generated TypeScript client"
date: 2026-11-08
tags: [concept, api, typescript]
---
# OpenAPI and the generated TypeScript client

## JSON
Data travels between frontend and backend as **JSON**, structured text:
```json
{ "name": "J. Allen", "position": "QB", "projection": 22.4 }
```

## OpenAPI
A machine-readable description of every REST endpoint: its URL, inputs and the exact shape of what it returns. **FastAPI generates it automatically** from the Python type hints, at `/openapi.json`. It also powers interactive docs at `/docs`, where you can try every endpoint in the browser.

## The generated client
A tool (e.g. `openapi-typescript` + `openapi-fetch`, or `orval`) reads `openapi.json` and writes TypeScript code for the frontend:
```
FastAPI (Python types) ──▶ openapi.json ──▶ generated TS client ──▶ Next.js
```
So in Next.js you call `api.getMatchup({ leagueId, week })` with full autocomplete instead of hand-typing URLs and guessing response shapes.

## What it saves you from
The backend renames `projection` → `projected_points`. Without a generated client, the frontend shows `undefined` in production and nobody notices. With one, regenerating the client makes every screen that uses `.projection` a **build error**, caught in CI before shipping.

## In Sunday War Room
A `generate:api` script regenerates the client. CI fails if the committed client is out of date with the backend's spec.

Related: [REST vs GraphQL](REST-vs-GraphQL.md) · [ADR-014](../Decisions/ADR-014-API-REST-OpenAPI.md) · [CI/CD](CI-CD-GitHub-Actions.md)
