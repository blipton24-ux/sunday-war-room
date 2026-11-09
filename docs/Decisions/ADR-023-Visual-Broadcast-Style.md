---
title: "ADR-023: Visual direction — game-day broadcast"
date: 2026-11-08
tags: [adr, design, ui]
status: superseded by ADR-032
---
# ADR-023: Visual direction — game-day broadcast

> [!NOTE]
> **Superseded** by [ADR-032](ADR-032-Visual-Sunday-War-Room-Style.md) (Sunday War Room style, flat). Kept for history.

## Options considered
| Option | Feel | Trade-off |
|---|---|---|
| **Game-day broadcast** | Bold, energetic: TV score-bug style, big numbers, dark base, strong accent, live scoreboards | Needs care to stay readable for dense tables |
| Clean analytics dashboard | Calm, neutral, data-dense tables and small charts | Great for analysis, flat on game day |
| Friendly and playful | Rounded cards, bright colors, emoji badges, casual copy | Can feel less serious as an analytics tool |

## Decision
Game-day broadcast. It fits the "command center" name and the live dashboard, and makes memorable screenshots. **It's an original design**, not modeled on any existing app or network's graphics.

Sketch (Week 10 matchup):
```
╔═════════════════════════════════╗
║  WEEK 10        ● LIVE  Q3 4:12 ║
║  ME        112.4  vs  98.7  OPP ║
║  proj 131.0 ██████░░  win 71%   ║
╚═════════════════════════════════╝
 QB  J. Allen     24.1 ▲  │ 18.3
 RB  B. Robinson  12.6    │ 9.8
```

## Implementation notes
- **Semantic design tokens** (`surface`, `ink`, `line`, `accent`, `positive`/`negative`) in Tailwind, never redefining Tailwind's built-in palettes (a lesson from the old project).
- Detail screens (projection factors, tables) use a calmer density inside the broadcast frame.

Related: [ADR-024 Theme](ADR-024-Theme-Dark-First.md) · [ADR-025 Navigation](ADR-025-Navigation-Bottom-Tabs.md) · [UI Screens](../Specs/UI-Screens.md)
