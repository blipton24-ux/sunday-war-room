---
title: "ADR-046: Every feature adapts to the league's own settings"
date: 2026-11-09
tags: [adr, product, leagues]
status: accepted
---
# ADR-046: Any league, any scoring, any waiver system

## Context
Leagues differ in scoring, roster slots and waiver rules (for example: 12 teams, full PPR, waiver priority during the claim window and then free agency; others use a FAAB budget). Waivers and trades depend on all of these.

## Decision
Nothing assumes a league format. Every feature reads the league's settings from its platform:
- **Waivers:** type (rolling priority, reverse standings, FAAB budget with a minimum bid) and claim window (days a dropped player stays on waivers, weekly waiver day, daily waivers), so each player shows "on waivers until …" or "free agent, add now".
- **Rosters:** any slot list (superflex, 2QB, extra flex, K or DEF on or off); IR/reserve and taxi slots are not counted as starters or bench depth.
- **Scoring:** the league's own rules; rules we can't score yet stay visible, never silently dropped (P1 behaviour).
- **Not yet:** individual defensive players (IDP) show "not projected yet" until P5 ([ADR-043](ADR-043-Phases-Renumbered.md)).

Tests cover several formats (superflex, 2QB, FAAB and priority waivers, IR/taxi, K/DEF off) rather than one example league.

Related: [ADR-047 Waivers](ADR-047-Waivers-Value-Added.md) · [ADR-048 Trades](ADR-048-Trades-Lineup-Impact.md) · [Adapter Pattern](../Concepts/Adapter-Pattern.md)
