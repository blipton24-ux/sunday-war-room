---
title: "ADR-012: Frontend — Next.js + React + TypeScript"
date: 2026-11-08
tags: [adr, frontend]
status: accepted
---
# ADR-012: Frontend stack — Next.js + React + TypeScript

## Context
Sunday War Room is a public, responsive web app that installs as a PWA ([ADR-010](ADR-010-PWA.md)). We need the tools that build the part users see and click. What each piece *is*: [TypeScript, React and Next.js](../Concepts/TypeScript-React-NextJS.md).

## Options considered
| Option | Upside | Downside |
|---|---|---|
| **Next.js + React** | React has the largest ecosystem and community; Next.js adds routing, server rendering (fast first load, readable by search engines), build optimization; straightforward PWA | Steeper learning curve than plain React |
| React + Vite single-page app | Same as the old projects; simpler | Slower first load; weaker for search engines |
| SvelteKit | Less code, very fast pages, loved by developers | Smaller ecosystem and fewer component libraries |

## Decision
- **Next.js (App Router) + React + TypeScript**
- Styling: **Tailwind CSS + shadcn/ui** components (owned, restylable, accessible)
- Data fetching: **TanStack Query** (caching, refetching, loading states)
- PWA: service worker + web push

## Why
Mainstream, well-supported technology ([ADR-004](ADR-004-Production-Grade-Bar.md)) and the right fit for a public site: server rendering gives fast first loads and search-engine-readable pages.

## Trade-offs accepted
More concepts to learn (server vs client components). In Sunday War Room, Next.js is **screens only**: all data and logic live in the FastAPI backend ([ADR-013](ADR-013-Backend-FastAPI.md)), which limits that complexity.

Related: [TypeScript, React, Next.js](../Concepts/TypeScript-React-NextJS.md) · [ADR-014 REST + OpenAPI](ADR-014-API-REST-OpenAPI.md) · [UI Screens](../Specs/UI-Screens.md)
