---
title: "P3 Build Plan"
date: 2026-11-10
tags: [build-plan, p3]
---
# Phase 3 Build Plan: ESPN adapter

Decisions: [ADR-050](../Decisions/ADR-050-Yahoo-Phase-7-Deploy-Phase-8.md) (phase order) · [ADR-051](../Decisions/ADR-051-ESPN-Access-Link-First-Cookie-Fallback.md) (access) · [ADR-052](../Decisions/ADR-052-Credential-Encryption.md) (encryption) · [ADR-053](../Decisions/ADR-053-ESPN-Client-Own-Code.md) (own client, approved reuses). Not in P3: Yahoo (P7), deploy and push alerts (P8), model upgrades (P4).

The owner's league is private and he is not the commissioner, so the cookie path is the real test.

## Build order
Each step ends runnable, tested, committed and green in CI.

1. **Docs and decisions** (ADR-050 to 053, this plan, vault renumbering).
2. **Adapter registry:** `LeagueAdapter` keeps the league reads; Sleeper-only discovery moves to its own protocol; `adapters/registry.py` picks the adapter by `league.platform`; worker, `sync_league_job` and `live_update_job` use it.
3. **Sync not tied to Sleeper:** remove the `sleeper_id`-only assumptions in `services/sync.py`, `waivers.py`, `projections.py`; `resolve_player_ids` (platform id, team defenses, name + position + team fallback with an unmatched log).
4. **Encryption and schema:** `app/crypto.py` (MultiFernet), `CREDENTIALS_KEYS`, credentials and status columns, per-follow pause status, log scrubbing, key-rotation script.
5. **ESPN raw client** (`adapters/espn.py`) with shape checks, retries, fixtures.
6. **ESPN mapping** to the common types; head-to-head points leagues only.
7. **ESPN scoring map** (`espn:` rule names; step rules, game bonuses, ladders, touchdown groups).
8. **Coverage and golden tests:** every ESPN stat id mapped or listed as unsupported; our score of a recorded week matches ESPN's per-player totals.
9. **Connect API:** probe a league link, save cookies (encrypted), email-a-link, disconnect; regenerate the OpenAPI client.
10. **Worker jobs:** list the user's leagues and team; syncs use the follower's own cookies only; expired cookies pause that user's league.
11. **Live:** per-platform refresh, skip paused leagues, cap concurrent ESPN requests.
12. **Web onboarding:** ESPN path with the guided cookie screen, consent text, phone "email me a link"; remove Sleeper-only wording.
13. **Settings and reconnect banner.**
14. **Scrubbed fixtures and end-to-end tests** with an ESPN stand-in server.
15. **Real-league check** with the owner's cookies; results into Verification Gaps and the backlog.

## Verification checklist
- [ ] A public ESPN league connects from a pasted link with no cookies.
- [ ] A private league connects with pasted cookies; the user's leagues are listed and their team is preselected.
- [ ] Waivers, trades, lineup and live work on an ESPN league.
- [ ] Our score for a finished week matches ESPN's per-player totals within 0.01 for rules computed exactly.
- [ ] Expired cookies pause only that user's league and show a reconnect banner.
- [ ] Cookies appear nowhere in logs, job arguments, API responses or committed fixtures.
- [ ] pytest, Vitest and Playwright pass locally and in GitHub Actions.

Related: [P2 Build Plan](P2-Build-Plan.md) · [Later Phases Outline](P2-P4-Outline.md) · [Features by Phase](../Specs/Features-by-Phase.md)
