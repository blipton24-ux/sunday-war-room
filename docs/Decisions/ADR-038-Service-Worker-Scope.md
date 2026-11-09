---
title: "ADR-038: What the service worker caches (P1: static files and an offline page only)"
date: 2026-11-09
tags: [adr, pwa, privacy, ui]
status: accepted
---
# ADR-038: What the service worker caches (P1: static files and an offline page only)

## Context
[ADR-010](ADR-010-PWA.md) makes Sunday War Room an installable PWA, and the [PWA concept note](../Concepts/PWA.md) lists "show the last data if the connection drops" as one benefit. P1 needs a service worker for installability and for the P2 push alerts. The open question is how much it should cache. Caching user data is a feature with trade-offs, and the vault doesn't settle it.

**This is a conservative default chosen while building P1, not an owner decision.** The offline-data option below is queued as [U-11 in the Improvement Backlog](../Build-Plan/Improvement-Backlog.md) for the owner to decide.

## Options considered — Jordan opens the Week 10 lineup on a train with no signal
```
A Static files + offline page:  phone shows "You're offline. Try again."
                                (app code is cached, so it opens fast; no league data is stored)
B Also keep last-known data:    phone shows the Week 10 lineup "as of 12:05", greyed out
                                (a copy of Jordan's last matchup/lineup is stored on the phone)
```
| | **A: Static files + offline page** | B: Plus last-known data |
|---|---|---|
| Works with no signal | A friendly message only | Last numbers, marked as old |
| User data stored on the device | None | Lineups, scores, league names |
| Shared or lent phone | Nothing to see | Needs clearing on sign-out, and must be per user |
| Risk of acting on stale numbers | None | Real: a "projection" hours old on game day, unless it is clearly marked |
| Work and test burden | Small, fully unit tested | Storage design, expiry, sign-out cleanup, "as of" UI, offline behavior of every screen |

## Decision
**A.** The worker (`web/public/sw.js`):
- Precaches `/offline.html` (self-contained, no external files) and the app icons.
- **Page loads:** network first; on a network failure it shows the offline page. Pages are never stored. A server error (for example a 502) is passed through, not disguised as "offline".
- **`/_next/static/*`:** cache first. These files have a content hash in their name and never change, so a cached copy cannot be stale. The cache is capped at 120 files, oldest dropped first.
- **Never touches** `/api/*`, other websites, or any non-GET request. Nothing about a user is cached, so there is nothing to leak or to clear on sign-out.
- Registers only in production builds (a worker in development would serve stale files while editing).

`web/test/sw.test.ts` runs the real `sw.js` in a sandbox and checks each rule, including three request types for every API path (a page load matters: a magic link arrives as one). Breaking either privacy rule on purpose makes tests fail.

## Why
Installable and fast, with no user data on the device and no stale-number risk. The data-caching feature can be added later without changing this worker's rules for everything else.

## Trade-offs accepted
Offline users see a message, not their lineup. On a very slow ("lie-fi") connection, where a request neither succeeds nor fails, the browser's own timeout applies before the offline page appears ([Verification Gaps](../Build-Plan/Verification-Gaps.md), V-20).

Related: [ADR-010 PWA](ADR-010-PWA.md) · [PWA concept](../Concepts/PWA.md) · [ADR-036 API access](ADR-036-API-Access-Through-Web-Server.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md)
