---
title: "ADR-025: Navigation — bottom tab bar"
date: 2026-11-08
tags: [adr, design, ui]
status: accepted
---
# ADR-025: Navigation — bottom tab bar (sidebar on desktop)

## Options considered
| Option | Upside | Downside |
|---|---|---|
| **Bottom tab bar** | Thumb-friendly; the standard for mobile apps; one tap between screens | Room for about 5 tabs |
| Hamburger menu (☰ drawer) | Cleaner look | Extra tap for every switch; harder one-handed |

## Decision
Mobile: a bottom tab bar with **Home · Lineup · Matchup · Chat · More**, where **More** opens Waivers, Trades and Accuracy. Desktop: the same items become a pill-shaped tab bar under the header (Sunday War Room style, [ADR-032](ADR-032-Visual-Sunday-War-Room-Style.md)). Features from later phases (Waivers/Trades P2, Chat P5 since [ADR-049](ADR-049-Phases-Reordered-ESPN-First.md)) show as "coming soon" until they ship.

*Updated 2026-11-08 with the v3 mockup: originally Home · Matchup · Lineup · Waivers · Chat with a desktop sidebar.*
```
┌──────────────────────────────┐
│        (screen content)      │
├──────┬──────┬──────┬─────┬───┤
│ Home │Lineup│Match │ Chat │More│
└──────┴──────┴──────┴─────┴───┘
```

Related: [ADR-010 PWA](ADR-010-PWA.md) · [UI Screens](../Specs/UI-Screens.md)
