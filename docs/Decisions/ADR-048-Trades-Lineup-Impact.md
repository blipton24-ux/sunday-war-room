---
title: "ADR-048: Trades judged by lineup impact"
date: 2026-11-09
tags: [adr, product, trades]
status: accepted
---
# ADR-048: Trade analyzer

## Options considered: you give one star WR for two good RBs
| | Sum of player values | **Lineup impact** |
|---|---|---|
| How | Add up each side's player values | Each team's best rest-of-season starting lineup, before vs after |
| The 2-for-1 | Looks like a win (two values beat one) | Only a win if the second RB would actually start; roster spots count |

Suggestions could be win-win trades, **best for me while still acceptable to them**, or both lists.

## Decision
- **Value = lineup impact** over the rest of the season, per team, under the league's rules ([ADR-046](ADR-046-Any-League-Settings.md)).
- **Any two teams** can be analyzed (for example a trade two other managers just made).
- **Suggestions: best for me, still acceptable.** The other team's lineup may lose at most a limit the user sets with a slider (default about 1 point per week).
- **This season only.** Dynasty and keeper leagues are labeled "this-season value"; future-season value comes with the model work in P4 ([ADR-049](ADR-049-Phases-Reordered-ESPN-First.md)).
- Recommendations only; trades are proposed in the platform's app.

Related: [ADR-047 Waivers](ADR-047-Waivers-Value-Added.md) · [P2 Build Plan](../Build-Plan/P2-Build-Plan.md)
