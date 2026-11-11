---
title: "ADR-045: Live updates by polling"
date: 2026-11-09
tags: [adr, live, frontend]
status: accepted
---
# ADR-045: Live delivery by polling

## Context
How updated scores reach an open screen during games. Closes Open Question #7 (originally pitched as WebSockets).

## Options considered
| | **Polling** | Server-Sent Events | WebSockets |
|---|---|---|---|
| Meaning | The page re-fetches every 30–60 s | The server pushes events over an open connection | Two-way open connection |
| Freshness | Limited by the source (Sleeper updates about once a minute) | Same source limit; saves up to one poll interval | Same |
| Fits | Snapshots of scores and win chance | An event feed such as a scoring-play ticker | Two-way traffic, which live scores don't have |
| Complexity | Lowest (a TanStack Query setting) | Redis pub/sub, streaming through the web server, reconnect catch-up | Highest |

## Decision
**Polling.** Sunday War Room is a strategy tool; people follow play-by-play in their fantasy platform's app. Live scope in P2: scores, each player's game status (yet to play / playing, with quarter and clock / done), live projected finals and win chance. No scoring-play ticker. A background job fetches each source once per league and game for everyone; screens re-fetch every 30–60 s **only while a relevant game is live**. Server-Sent Events are kept for streaming AI answers in the AI phase (P5, [ADR-049](ADR-049-Phases-Reordered-ESPN-First.md)).

Related: [ADR-044 Live data](ADR-044-Live-Data-Sources.md) · [ADR-036 API through the web server](ADR-036-API-Access-Through-Web-Server.md) · [P2 Build Plan](../Build-Plan/P2-Build-Plan.md)
