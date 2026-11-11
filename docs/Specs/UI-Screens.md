---
title: "UI Screens"
date: 2026-11-08
tags: [spec, ui, design]
---
# UI Screens

Style: Sunday War Room, flat, with player photos ([ADR-032](../Decisions/ADR-032-Visual-Sunday-War-Room-Style.md)) · dark-first with light toggle ([ADR-024](../Decisions/ADR-024-Theme-Dark-First.md)) · bottom tabs + More on mobile, pill tab bar on desktop ([ADR-025](../Decisions/ADR-025-Navigation-Bottom-Tabs.md)) · mobile-first.

**Visual reference:** `mockups/p1-screens-v3.html` (open in a browser). It's the agreed look; the real app should match it.

## Global
- **Header:** Sunday War Room logo + name, league switcher (league name as a menu, with sync status dot and "synced 3m ago"), week stepper, refresh, theme toggle.
- **Tabs:** Home · Lineup · Matchup · Chat (P5) · More (Waivers P2, Trades P2, Accuracy). Settings via the league menu.
- **States:** every screen has designed loading (skeletons), empty and error states.

## Screens (P1)
**Sign in:** logo, "Sign in with Google" and "Email me a link."

**Onboarding:** Sleeper username → list of leagues → pick your team in each → syncing progress → Home.

**Home:** title is the **current week** ("Week 10") with a status line ("2 games left"). Then:
- the matchup score header (both teams, live scores, Live pill, projected final, status chip like "😎 Cruising")
- **Heads up** alerts with player photos (on bye in lineup, questionable, booming)
- a **Fix my lineup** button
- the **How we've been doing** accuracy card

**Lineup:** score header, then the **lineup check** card (win-chance ring + swaps to make, e.g. "▲ Jennings ~~Addison~~ +11.2", "make the change in Sleeper"), the **Top performers** shelf, then Starters and Bench as player rows. Tap a row to expand: Bust → Proj → Boom range bar (solid segments), "why this number" chips, confidence, "frozen at kickoff."

**Matchup:** scoreboard card with previous/next matchup arrows ("1 / 5"), Live/Final pill, both teams' scores with projections, the split bar, and the **Projected to win** panel (ring, projected winner, projected final, win chance). Then starters side by side by slot with headshots, the leader's number in bronze.

**Accuracy:** past weeks, frozen projections vs actual results, explained in plain words.

**Waivers (P2):** a Rest of season / This week toggle; a card with the league's waiver rules (FAAB budget left, or claim position and claim window); then free agents that improve my best lineup, best first: points added per week, the player's own points per week, "Free agent · add now" or "On waivers until about Wed 9:00", a FAAB bid range, and who to drop. Empty states: free agents not projected yet, or nobody improves the lineup.

**Trades (P2):** the league's trade rules in the title (this-season value only for dynasty/keeper, trade deadline). "Ideas for you" with a slider for how much the other team may lose (0–3 pts/week, default 1), each idea showing what I give and get and both teams' change per week, with "Open in the analyzer". The analyzer: pick any two teams and the players each gives; the result shows each team's change per week, best lineup before → after, who has to be dropped, and the lineup after.

**Settings:** connected platforms, leagues, theme, sign out, delete account.

## Design system
- **Palette (dark):** surfaces `#0b1016` / `#141e28` / `#1a2733` / `#243341`; parchment ink `#efe8da` → `#5c6a78`; bronze accent `#e6b95c`; sea-steel `#7fa3bd` for section labels; ember `#e2683c` for Live/Bust; good `#3ddc97`, ok `#f5d36b`, bad `#ff5c6c`. A light parchment variant exists for the toggle.
- **No gradients.** Flat colors only; cards separate from the page by surface level, not borders.
- **Type:** Archivo (wide, 800–900) for scores and titles; Inter for text; tabular numbers.
- **Position colors** are consistent everywhere: QB `#fb7185`, RB `#34d399`, WR `#60a5fa`, TE `#fbbf24`, FLEX `#a3e635`, K `#c084fc`, DST `#22d3ee`.
- **Player avatars:** headshot on a flat tint of the team color, slot tag pinned bottom-left; team logo for defenses; initials fallback.
- Semantic Tailwind tokens (`surface`, `ink`, `line`, `accent`…), never redefining Tailwind's built-in palettes.
- Touch targets ≥ 44px; works one-handed.

Related: [ADR-032 Visual style](../Decisions/ADR-032-Visual-Sunday-War-Room-Style.md) · [Features by Phase](Features-by-Phase.md) · [PWA](../Concepts/PWA.md)
