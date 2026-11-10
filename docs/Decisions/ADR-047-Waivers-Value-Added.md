---
title: "ADR-047: Waivers ranked by value added to my lineup"
date: 2026-11-09
tags: [adr, product, waivers]
status: accepted
---
# ADR-047: Waivers

## Options considered
| Horizon | Good for | Weakness |
|---|---|---|
| This week only | Streaming, bye and injury fill-ins | Misses long-term pickups |
| Rest of season only | Long-term adds | Misses this week's emergency |
| **Both, with a toggle** | Either need | One more control |

## Decision
- Free agents are ranked by **value added to my best lineup**: how many projected points my best starting lineup gains with the player, over the **rest of the season (default)** or **this week** (toggle).
- Each suggestion names a **suggested drop**: the rostered player whose loss costs the least.
- Each player shows its status under the league's rules ([ADR-046](ADR-046-Any-League-Settings.md)): "on waivers until Wed 9:00, your claim position #4" or "free agent, add now".
- **FAAB leagues** get a suggested **bid range** (for example "$8–12 of your $63"), from value added and budget left, labeled as a guide. Priority leagues show the claim position instead.
- Recommendations only; claims are made in the platform's app ([Non-Goals](../Specs/Non-Goals.md)).

Related: [ADR-046 Any league](ADR-046-Any-League-Settings.md) · [ADR-048 Trades](ADR-048-Trades-Lineup-Impact.md) · [P2 Build Plan](../Build-Plan/P2-Build-Plan.md)
