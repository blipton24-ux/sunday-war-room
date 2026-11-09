---
title: "The adapter pattern (platform adapters)"
date: 2026-11-08
tags: [concept, architecture, design-pattern]
---
# The adapter pattern

**Problem:** Sleeper, ESPN and Yahoo each describe leagues differently (field names, IDs, scoring rules, login methods). If every feature handled all three formats, every feature would need three versions.

**Solution:** define **one interface**, the shape Sunday War Room wants, and write one **adapter** per platform that translates into it. *Like a travel plug adapter: your device has one plug; each country's adapter converts the wall socket to it.*

```python
class LeagueAdapter(Protocol):
    platform: Platform
    async def find_leagues(self, account: PlatformAccount, season: int) -> list[LeagueRef]: ...
    async def fetch_league(self, ref: LeagueRef) -> League: ...        # settings + scoring rules
    async def fetch_rosters(self, ref: LeagueRef) -> list[Team]: ...
    async def fetch_matchups(self, ref: LeagueRef, week: int) -> list[Matchup]: ...

class SleeperAdapter(LeagueAdapter): ...   # P1
class EspnAdapter(LeagueAdapter): ...      # P4 — needs user's cookies
class YahooAdapter(LeagueAdapter): ...     # P4 — needs OAuth
```

## Rules in Sunday War Room
- **Only an adapter talks to its platform.** Nothing else imports a platform client.
- Adapters return Sunday War Room's own types, never raw platform JSON (raw data may be stored for debugging).
- **Player IDs:** every platform has its own player IDs. A crosswalk maps them to one Sunday War Room player (nflverse's ID table). Guard against duplicate and missing rows in that source (a lesson from the old project).
- Adapters **fail soft** on legitimately missing fields (no injury status → "unknown") and **fail loudly** on shape changes (a renamed field raises a clear error rather than silently producing wrong data).

Related: [ADR-006](../Decisions/ADR-006-Platform-Adapters.md) · [Architecture](../Specs/Architecture.md) · [Job Queues](Job-Queues-and-Redis.md)
