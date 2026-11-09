---
title: "ADR-014: API style — REST + OpenAPI typed client"
date: 2026-11-08
tags: [adr, api, backend, frontend]
status: accepted
---
# ADR-014: API style — REST + OpenAPI-generated TypeScript client

## Context
How do the Next.js frontend and the FastAPI backend talk? Full explanation and side-by-side code: [REST vs GraphQL](../Concepts/REST-vs-GraphQL.md) and [OpenAPI typed client](../Concepts/OpenAPI-Typed-Client.md).

## Options considered
| | **REST + OpenAPI** | GraphQL |
|---|---|---|
| Who shapes the response | Backend (fixed URL → fixed shape: a "combo meal") | Frontend, per query (a "buffet") |
| Setup in FastAPI | Built in | Extra library, schema, resolvers |
| Caching | Easy (same URL = same answer) | Needs special client caching |
| Debugging | Read the URL in the network tab | Read query text in each request |
| Best when | One frontend, one backend (Sunday War Room) | Many different client apps |

## Decision
**REST**, versioned under `/api/v1/...`. FastAPI auto-generates an **OpenAPI** description of every endpoint, and a **TypeScript client is generated from it** for Next.js.

## Why
GraphQL's real strength (each client asks for different shapes without backend changes) matters most with many different apps. Sunday War Room has one. REST is built into FastAPI, caches easily, and is easier to debug while learning. The generated client gives the same compile-time safety GraphQL codegen would.

## Trade-offs accepted
Some endpoints return a few fields a screen doesn't use. The client must be regenerated when the API changes (a script, run in CI).

Related: [REST vs GraphQL](../Concepts/REST-vs-GraphQL.md) · [OpenAPI Typed Client](../Concepts/OpenAPI-Typed-Client.md) · [API spec](../Specs/API.md)
