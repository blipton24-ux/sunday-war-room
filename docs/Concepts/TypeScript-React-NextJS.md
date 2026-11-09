---
title: "TypeScript, React and Next.js"
date: 2026-11-08
tags: [concept, frontend]
---
# TypeScript, React and Next.js

In short: **TypeScript is the language, React is the building blocks, and Next.js is the house frame** that holds the blocks and turns them into a website.

## TypeScript: the language
Browsers only run JavaScript. TypeScript is JavaScript plus **types**: labels that say what kind of data something is.
```ts
type Player = { name: string; projection: number };
```
If code tries to use `player.projection` as text, or misspells it `player.projecton`, the editor flags it **before the app runs**. At build time TypeScript is converted to plain JavaScript. It exists to catch mistakes early.

## React: a library of components
You build the screen from **components**, reusable pieces of UI like `<PlayerCard>`, `<MatchupTable>`, `<StartSitBadge>`. You describe what the screen should look like *for the current data*. When the data changes (a player scores), React updates only the parts of the page that changed.

## Next.js: the framework around React
React only draws components. Next.js adds what a real website needs:
- **Routing:** the file `app/leagues/[id]/page.tsx` automatically becomes the URL `/leagues/123`.
- **Server rendering:** HTML can be built on a server, so pages appear fast and search engines can read them.
- **Build and optimization:** bundling, image handling, and sending each page only the code it needs.

## Supporting pieces in Sunday War Room
- **Tailwind CSS:** style with small utility classes (`text-2xl font-bold`) instead of separate CSS files.
- **shadcn/ui:** accessible, good-looking components copied *into* the project, so we own and restyle them.
- **TanStack Query:** fetches data from the API, caches it, refetches when stale, and tracks loading/error states.

## In Sunday War Room
Next.js is **screens only**. Every piece of data comes from the FastAPI backend through the generated API client ([OpenAPI Typed Client](OpenAPI-Typed-Client.md)).

Related: [ADR-012 Frontend](../Decisions/ADR-012-Frontend-NextJS.md) · [PWA](PWA.md) · [Backend Basics](Backend-Basics.md)
