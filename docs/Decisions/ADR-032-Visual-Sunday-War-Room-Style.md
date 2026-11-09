---
title: "ADR-032: Visual design — Sunday War Room style, flat"
date: 2026-11-08
tags: [adr, design, ui]
status: accepted
supersedes: ADR-023
---
# ADR-032: Visual design — the Sunday War Room style, flat (supersedes ADR-023)

## Context
Three clickable mockups were compared (in `mockups/`):
| Mockup | Style | Outcome |
|---|---|---|
| v1 | Game-day broadcast ([ADR-023](ADR-023-Visual-Broadcast-Style.md)) | Replaced |
| v2 | Sunday War Room style, with gradients | Improvement, but gradients and no player photos |
| **v3** | **Sunday War Room style, flat, real player photos** | **Chosen** |

The Sunday War Room style comes from the owner's earlier prototype of the same name.

## Decision
The UI follows the Sunday War Room design system ([UI Screens](../Specs/UI-Screens.md)):
- **"Odyssey" palette:** storm-blue surfaces (`#0b1016` → `#243341`), bronze accent `#e6b95c`, parchment text `#efe8da`, sea-steel `#7fa3bd` for section labels, ember `#e2683c` for Live/Bust; green/yellow/red bands for odds.
- **No color gradients anywhere.** Flat colors only; cards separate from the page by a lighter surface, not borders.
- **Type:** Archivo (wide, extra-bold) for scores and titles; Inter for everything you read; tabular numbers.
- **Player photos:** headshots on a flat tint of the team color with the slot pinned to the avatar; team logos beside names and for defenses; initials when no photo exists.
- **Components:** win-chance ring, lineup-check card, "Top performers" shelf, tap-to-expand player rows with a Bust → Proj → Boom range bar, Live/Final pills, Boom/Bust tags.
- **Matchup:** scoreboard with matchup arrows, split bar, and a **"Projected to win"** panel (ring + projected winner + projected final + win chance), then starters side by side.
- **Home:** title is the **current week** ("Week 10"), then the score header, Heads-up alerts, "Fix my lineup", and the accuracy card.
- Dark-first with the light toggle from [ADR-024](ADR-024-Theme-Dark-First.md) kept.

## Why
It's a proven design the owner already likes. Removing gradients makes it cleaner and easier to build consistently.

## Trade-offs accepted
Player headshots come from ESPN's public image CDN. The production app must cache or proxy them and fall back to initials ([Open Questions](../Specs/Open-Questions.md)).

Related: [ADR-033 Name](ADR-033-Name-Sunday-War-Room.md) · [ADR-025 Navigation](ADR-025-Navigation-Bottom-Tabs.md) · [UI Screens](../Specs/UI-Screens.md)
