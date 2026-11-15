---
title: "ADR-053: ESPN client written in-house, with approved rewrites of earlier lessons"
date: 2026-11-10
tags: [adr, integrations, process]
status: accepted
---
# ADR-053: ESPN client and approved reuses

## Context
The earlier fantasy app reached ESPN through the `espn_api` library and found its limits: the library drops per-position scoring overrides (a tight-end premium is read as the base value) and hides ESPN's raw data, so format changes go unnoticed. It also learned many ESPN quirks by trial and error. [ADR-002](ADR-002-Fresh-Build.md) requires approval for each reuse.

## Options considered
| Option | Result |
|---|---|
| `espn_api` library | Fast start; known scoring gaps; no shape checks |
| **Own client plus rewritten lessons** | Same retry and fail-loudly pattern as the Sleeper adapter; known quirks not relearned |
| Fresh, no reuse | Quirks rediscovered through bugs |

## Decision
**Our own httpx client** (`adapters/espn.py`), built like the Sleeper adapter: pydantic models of ESPN's raw responses, an error when ESPN changes shape, retries that respect rate limits, tests on recorded responses.

**Approved for rewrite (not copy), amending [ADR-031](ADR-031-Approved-Reuses.md):**
- The list of ESPN quirks (omitted zero-valued rules, band boundaries such as 350 to 399 yards allowed, a future week silently returning the current week).
- ESPN to nflverse team code fixes and a table from ESPN's numeric team ids.
- The call that lists a signed-in user's leagues and their own team.
- The scoring table including **step rules** ("1 point per 10 yards") and **game bonuses** ("+3 for a 100-yard game") in addition to the three shapes already approved.

Not reused: the library itself, the desktop-window cookie capture, and any other module.

ESPN rules get their own names (`espn:<ABBR>`, with `@<POS>` for per-position overrides) rather than being converted into Sleeper's names, because ESPN's bands do not line up with Sleeper's and converting would lose information.

Related: [ADR-031](ADR-031-Approved-Reuses.md) · [ADR-051](ADR-051-ESPN-Access-Link-First-Cookie-Fallback.md) · [ADR-044 Live data](ADR-044-Live-Data-Sources.md) · [Adapter Pattern](../Concepts/Adapter-Pattern.md)
