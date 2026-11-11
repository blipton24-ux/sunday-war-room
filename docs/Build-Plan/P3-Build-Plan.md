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
2. **Adapter registry** (done 2026-11-10): `LeagueAdapter` keeps the league reads; Sleeper-only discovery moves to its own protocol; `adapters/registry.py` picks the adapter by `league.platform`; worker, `sync_league_job` and `live_update_job` use it.
3. **Sync not tied to Sleeper** (done 2026-11-10; ESPN team ids and D/ST ids in `adapters/espn_teams.py`, to be confirmed against a real league in step 15): remove the `sleeper_id`-only assumptions in `services/sync.py`, `waivers.py`, `projections.py`; `resolve_player_ids` (platform id, team defenses, name + position + team fallback with an unmatched log).
4. **Encryption and schema** (done 2026-11-10): `app/crypto.py` (MultiFernet), `CREDENTIALS_KEYS` (the API refuses the public dev key in production), `platform_accounts.credentials_encrypted` / `status` / `credentials_checked_at`, and `league_memberships.platform_account_id` (which account's cookies each follower reads with, so one member's expired cookies never touch another's), log scrubbing, `python -m app.scripts.rotate_credentials`.
5. **ESPN raw client** (done 2026-11-10; `adapters/espn.py`): our own httpx client with pydantic shape checks, retries that honour `Retry-After`, cookies sent per request and never stored on the shared client, `EspnCredentials` that never print their secrets. Tested on synthetic, scrubbed fixtures (`tests/espn_fixtures.py`).
6. **ESPN mapping** (done 2026-11-10): lineup slots (IDP slots count as bench), waiver and season rules, two-week playoff rounds (the week's own points), transactions, name hints for player matching; head-to-head points leagues only. A sync also now de-duplicates transactions a platform reports twice.
7. **ESPN scoring map** (done 2026-11-10; `model/scoring_espn.py`): `espn:` rule names, a new step shape, per-position overrides (a zero override still switches a rule off), open-ended field-goal ladders, touchdown groups, and a plain reason for every rule we can't score.
8. **Coverage tests** (done 2026-11-10): all 235 ESPN stat ids are scored or explained, and every rule reads only stat columns we load. **Still to do in step 15:** the golden test of our score against ESPN's own per-player totals for a real finished week. Everything ESPN-shaped so far is written from earlier knowledge of the API, not from a real response, so step 15 is where it is proven.
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
