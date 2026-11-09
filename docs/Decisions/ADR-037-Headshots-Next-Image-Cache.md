---
title: "ADR-037: Player photos through the Next.js image cache"
date: 2026-11-09
tags: [adr, design, ui, images]
status: accepted
---
# ADR-037: Player photos are served through the Next.js image cache

## Context
Headshots and team logos come from ESPN's public image CDN ([ADR-032](ADR-032-Visual-Sunday-War-Room-Style.md)); the API returns their URLs. [Open question #13](../Specs/Open-Questions.md) asked how the app should load them.

## Options considered — the Lineup screen shows 9 starters' photos on a phone
```
A Next.js cache:  browser --/_next/image?url=<espn>&w=96--> Next.js --(first request only)--> ESPN
                  every later view: Next.js serves its resized, cached copy
B Direct:         every browser downloads every full-size image from ESPN
C Own copies:     nightly job copies images into our storage; browsers load them from there
```
| | **A: Next.js image cache** | B: Direct from ESPN | C: Own stored copies |
|---|---|---|---|
| Size on phones | Resized for the slot | Full size | Resized |
| If ESPN changes or blocks a link | Already-cached images keep working | Initials everywhere | Keeps working |
| Who ESPN sees | Our server | Every user | Our job |
| Work and cost | Built into Next.js (`next/image`) | None | Storage, a job, a monthly bill |

## Decision
**A.** Images render with `next/image`; `images.remotePatterns` allows only ESPN's headshot and team-logo paths. Any image that fails to load falls back to the player's initials (or team abbreviation) on the team-color tint.

## Why
Faster on phones and resilient to ESPN changes for very little code.

## Trade-offs accepted
- The image optimizer needs the `sharp` library on the server (standard in the Docker image; checked on Windows development machines).
- The web server does the first fetch of each image and stores the cache on its disk, which is reset on redeploy (the images are simply fetched again).
- Showing ESPN's images in a public app should be checked against ESPN's terms before launch: tracked as U-06 in the [Improvement Backlog](../Build-Plan/Improvement-Backlog.md). Option C stays available if that check requires it.

Related: [ADR-032 Visual style](ADR-032-Visual-Sunday-War-Room-Style.md) · [UI Screens](../Specs/UI-Screens.md) · [Open Questions](../Specs/Open-Questions.md)
