---
title: "Improvement Backlog"
date: 2026-11-09
tags: [build-plan, backlog, model, ui]
---
# Improvement Backlog

Known gaps and upgrades we have chosen to defer, with the evidence for each. It is a list of **things to improve**, not decisions: anything that needs a choice follows [ADR-003](../Decisions/ADR-003-Documentation-Standard.md) and becomes an ADR when picked up. Questions that block a build step live in [Open Questions](../Specs/Open-Questions.md) instead.

**How to use it**
- Add an item the moment we notice one (with the measurement or incident behind it), even if we won't act soon.
- IDs are permanent (`M-` model, `U-` UI, `P-` platform/ops). Reference them in commits and ADRs.
- When an item is picked up, link the ADR or PR in the Status column; when it ships, move the row to **Done** at the bottom.
- Model changes follow [ADR-034](../Decisions/ADR-034-Ship-Model-v1-Upgrade-Later.md): a new version ships only if it beats model 1.0.0 on held-out weeks, including the startable-player slice, and reusing any technique from the earlier project needs its own approval ([ADR-002](../Decisions/ADR-002-Fresh-Build.md)).

Priority: **High** = fix before it can mislead a user or lose data · **Med** = clear user-visible gain · **Low** = polish or later phase.

## Projection model

Baseline to beat (held-out 2024 / 2025, weeks 5–18, full PPR, average miss in points; see [ADR-034](../Decisions/ADR-034-Ship-Model-v1-Upgrade-Later.md)): startable players 6.35 / 6.45 for model 1.0.0, against 6.26 / 6.50 for a plain season average and 5.78 / 5.83 for the earlier project's model.

| ID | Item | Evidence | Priority | Needs | Status |
|---|---|---|---|---|---|
| M-01 | **Keep past weeks visible across model versions.** Screens and the Accuracy page only read rows with the *current* `model_version`, so after the first version bump every past week's frozen projections disappear and the accuracy history restarts. Read each week's frozen row from the version that froze it; keep grading per version. | `views.load_week`, `views.accuracy_view` and `projections.compute_projections` all filter `model_version == MODEL_VERSION` | **High** (before the first bump) | A small design note: which version a past week shows, and how the Accuracy page compares versions | Open |
| M-02 | **Per-position models on expected fantasy points** (opportunity quality) instead of recent points alone. | The earlier project's version improved startable-player error at every position in both held-out seasons | High | ADR-002 reuse approval; must beat 1.0.0 on the startable slice | Open |
| M-03 | **Depth-chart rank adjustment for RB / WR / TE** (v1 adjusts backup QBs only). | The earlier project found a monotonic residual by depth rank at every position and improved ordering everywhere | Med | ADR-002 approval; needs depth-chart data ingested (nflverse `load_depth_charts`, shape changed in 2025) | Open |
| M-04 | **Project team defenses from the opponent's betting total** instead of the defense's own history. | v1 defense rank correlation is 0.17 (held-out 2025); the earlier project measured a defense's own recent scoring as no better than a constant | Med | ADR-002 approval; needs a betting-line source | Open |
| M-05 | **Better starting point for players with no history** (rookies, veterans back from a missed season): draft round and depth rank instead of a flat 30th-percentile value. | v1 treats a first-round rookie and an undrafted one the same; the earlier project's fitted values differed by roughly 3–4x between them at RB, WR and TE | Med | ADR-002 approval; needs draft-pick data (`load_draft_picks`) | Open |
| M-06 | **Season-opener (weeks 1–4) handling measured separately.** Report weeks 1–4 and 5+ apart, then tune the last-season blend weight, which is a fixed 3 games. | The Backtest Report mixes both; the earlier project measured weeks 1–4 as a distinctly harder problem (error 4.63 vs 4.51 in-season) and found defects that only the opener exposed | Med | Backtest report change first (see M-09) | Open |
| M-07 | **Correlated simulation**: a QB and his own receivers should move together; v1 draws every player independently. | The earlier project measured QB↔WR +0.20 and QB↔TE +0.21 at player level, and near zero for two receivers on one offense | Low | ADR-002 approval; changes win probabilities, not projections | Open |
| M-08 | **Ranges fitted to each league's scoring.** Ranges are fit in half-PPR and applied to every league (a v1 simplification, stated in the Projection Model spec). | Scoring changes the spread of outcomes, and range coverage for other scoring formats hasn't been measured | Med | Refit per scoring family, or scale by projected points; verify 80% coverage per family | Open |
| M-09 | **Backtest report upgrades**: add the startable-player slice (top 15 QB/TE, top 36 RB/WR per week), weeks 1–4 vs 5+, and a full-PPR option, so it measures what start/sit needs. | The comparison in ADR-034 had to be run by hand; the committed report's "all players" number is dominated by backups | **High** (gates every other model item) | None | Open |
| M-10 | **Fresher injury status.** Injury and depth data come from Sleeper's player list, refreshed at most daily. A starter ruled out on Sunday morning is still projected as healthy. | The earlier project traced about 0.26 of a 0.45-point miss to ESPN to exactly this | **High** | A source or cadence decision (Sleeper asks for at most one full-list fetch a day); possibly nflverse injuries or recomputing near kickoff | Open |
| M-11 | **Record injury and depth-chart snapshots at every compute**, so a future model can be trained and backtested on them. | v1's injury and backup-QB factors can't be backtested because no history exists | Med | A new table and migration | Open |
| M-12 | **Score special-teams fumble rules** (`st_ff`, `st_fum_rec`, `def_st_ff`, `def_st_fum_rec`). | The fixture league uses all four; nflverse weekly stats don't break them out, so the API lists them under `unsupported_rules` rather than guessing | Low | A source (play-by-play or another dataset); UI shows the note meanwhile (U-03) | Open |
| M-13 | **Link rookies missing from nflverse's ID table.** A player with no `gsis_id` has no history and gets the generic prior. | CJ Daniels (WR, LA, `years_exp` 0) was the only unlinked rostered player of 313 | Low | A name + team + position match with an ambiguity guard; never guess | Open |
| M-14 | **Weekly auto-refit of ranges with a promotion gate** (listed in the Projection Model spec under later upgrades). | Calibration is fitted once, by hand, from the backtest | Low | Needs M-09 and enough live weeks | Open |
| M-15 | **Rest-of-season value model** for waivers and trades (P2). v1 projects the current week only. | The earlier project found a one-week projection is a poor stand-in for a season-long value and built a separate model | Low (P2) | P2 spec | Open |
| M-16 | **Weak spots to watch**: running backs are slightly worse than the season-average baseline (MAE 4.12 vs 4.08); quarterbacks, kickers and defenses order poorly (rank correlation 0.45 / 0.13 / 0.17). | [Backtest Report](Backtest-Report.md), held-out 2025 | Info | Re-read after each model change | Open |

## UI

The web app isn't built yet (P1 step 11), so this list starts with what the API and mockup already tell us and grows as screens are built.

| ID | Item | Evidence | Priority | Needs | Status |
|---|---|---|---|---|---|
| U-02 | **Accuracy page before the first graded week.** It is empty until a week of genuine pre-kickoff projections finishes, so it needs an honest empty state that says what is measured and when numbers will appear. | The API returns `n: 0` and null metrics until then | Med | Copy and a layout for the empty state | Open |
| U-03 | **Show scoring rules we can't score.** The matchup, lineup and player endpoints return `unsupported_rules`; the UI should say so near the projection instead of hiding it. | API contract; relates to M-12 | Med | Wording | Open |
| U-04 | **Games in progress.** A player whose game has started shows the pre-game projection and no partial score. Label it clearly until live scores exist (P2). | `game_status: in_progress` has no points attached | Low (P2) | Live dashboard design | Open |
| U-05 | **Explain the numbers on screen**: "why this number" factors, the 80% range, and "frozen at kickoff" need one short plain-language explanation reachable from every projection. | The API returns `factors`, ranges and `frozen`; the mockup shows chips | Med | Copy | Open |
| U-06 | **Check ESPN's terms for showing their player images** in a public app before launch. If they don't allow it, switch to stored copies or another image source (option C in ADR-037). | ADR-037 trade-offs | **High** (before public launch) | Read the terms; owner decision if a change is needed | Open |
| U-07 | **"Projected final" while games are live** can read below the current score: players in progress keep their pre-game projection while the score already includes their points. | Seen 2026-11-09: projected 133.9 against a live 151.1 | Med | Live per-player points (P2 live dashboard) | Open |
| U-08 | **Browse the league's other matchups** (mockup v3's "1 / 5" arrows). The API returns only your own matchup. | Matchup screen shows one board | Low | An endpoint for all matchups of a week | Open |
| U-09 | **Phone-size check of every screen.** Screens were checked in a desktop window; the browser window couldn't be resized to phone width. Bottom tabs and layouts use standard breakpoints but haven't been looked at at 390 px. | Visual check 2026-11-09 | **High** (P1 step 14) | Playwright run at a phone viewport | Open |
| U-10 | **Compare against the platform's own projections** on the Accuracy page (mockup v3 says "closer than Sleeper on 58% of players"). We don't store Sleeper's projections, so the line was left out rather than invented. | Mockup vs data | Low | Store Sleeper's weekly projections when we freeze ours | Open |

## Platform and tooling

| ID | Item | Evidence | Priority | Needs | Status |
|---|---|---|---|---|---|
| P-01 | **Lock Python dependencies.** `pyproject.toml` has lower bounds only, so a fresh install gets whatever is newest. Add a lockfile before the Dockerfiles (step 13) so CI and production match local. | No lock exists; versions were resolved on 2026-11-08 | **High** (do in step 13) | Pick a lock tool (`pip-tools` or `uv`; `uv` couldn't be installed on this machine earlier) | Open |
| P-02 | **Windows Smart App Control blocks unsigned native files.** Rollup's native file was refused in step 10; since then Vitest 5 (Rolldown), Next.js 16 and its image library all load fine, and the Rollup workaround was removed. Still to check: Playwright's browsers (step 14). Fallback: run those in Docker. | `Application Control policy has blocked this file`; `VerifiedAndReputablePolicyState = 1` | Low | Nothing unless a tool has no fallback | Open |
| P-03 | **Windows Polars build.** The default build hangs at import on this CPU; the compatibility build (`polars[rtcompat]`) is installed locally. Make sure Docker and CI install what they need and the README note stays accurate. | `api/README.md` | Low | None | Open |
| P-04 | **Per-user rate limits beyond refresh** (before the chat in P3). | Only manual refresh is limited today | Low (P3) | P3 spec | Open |
| P-05 | **Better Auth's schema check warns** "user_id … expected string but got int4" for `sessions` and `accounts`. Harmless today (integer ids are a supported mode and sign-in works end to end), but re-check after Better Auth upgrades. | `npm run auth:schema` output | Low | None | Open |
| P-06 | **No linter for the web app yet.** Next.js 16 removed `next lint`; add ESLint (flat config, Next + React hooks rules) before CI. | Only `tsc` and Vitest run today | Med (P1 step 15) | None | Open |

## Done

| ID | Item | Where |
|---|---|---|
| U-01 | Player headshots: decided to serve them through the Next.js image cache with an initials fallback | [ADR-037](../Decisions/ADR-037-Headshots-Next-Image-Cache.md) |

Related: [Backtest Report](Backtest-Report.md) · [P1 Build Plan](P1-Build-Plan.md) · [P2–P4 Outline](P2-P4-Outline.md) · [Projection Model](../Specs/Projection-Model.md) · [Open Questions](../Specs/Open-Questions.md) · [ADR-034](../Decisions/ADR-034-Ship-Model-v1-Upgrade-Later.md)
