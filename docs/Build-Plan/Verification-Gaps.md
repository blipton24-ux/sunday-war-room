---
title: "Verification Gaps"
date: 2026-11-09
tags: [build-plan, testing, qa]
---
# Verification Gaps

Things that are **built but not yet seen working** in a real browser or with real services. Each was covered by type checks, unit tests or API tests, but nobody has watched it work end to end. This is different from the [Improvement Backlog](Improvement-Backlog.md), which lists things we know we want to change.

**How to use it**
- When an item is tested, fill in the date and result, and move the row to **Verified** at the bottom. If the test finds a bug, fix it or add it to the backlog, and link it here.
- IDs are permanent (`V-`). Add a row whenever something ships without being watched working.
- Most items belong in the Playwright end-to-end tests ([P1 Build Plan](P1-Build-Plan.md) step 14). The column says which ones need a person or real credentials instead.

## Flagged after the P1 step 11 check (2026-11-09)

| ID | What isn't verified | Why not | How to test | Where | Status |
|---|---|---|---|---|---|
| V-01 | **Every screen at phone size**: bottom tabs and More menu, header fit (league name, week stepper, refresh and theme buttons), player rows, head-to-head avatars hidden under 420 px, Top performers shelf scrolling, 44 px touch targets | The browser window couldn't be resized to phone width; only desktop width was seen | Playwright at 390×844, plus one look on a real phone | Playwright + phone | Open (backlog U-09) |
| V-02 | **"Week N isn't here yet"** on Home, Lineup and Matchup for a future week, and its "Back to Week N" button | The browser tools failed before the check; only type-checked and built | Step the week forward past the current week | Playwright | Open |
| V-03 | **"Projected final" while games are live** can read below the live score | Known behavior, not a test gap: players in progress keep their pre-game projection. The real fix needs live scores (P2) | During a live game, compare the header's projected final with the score; re-check after the P2 live work | Sunday, by hand | Open (backlog U-07) |

## Also not yet seen working

| ID | What isn't verified | Why not | How to test | Where | Status |
|---|---|---|---|---|---|
| V-04 | **Expanded player row with a projection**: Bust → Proj → Boom bar, "why this number" chips and notes, "Updates until kickoff" / "Frozen at kickoff" | The only row expanded (a finished game) had no projection, so only "recent games" showed | Expand a starter before kickoff and after kickoff | Playwright | Open |
| V-05 | **Lineup check with swaps**: swap rows (▲ in, ~~out~~, +gain), win chance before → after, "Start" tag on bench players | Every game in the test week was final, so the lineup was already optimal | Test a week before kickoff where a bench player outprojects a starter (fixture data) | Playwright | Open |
| V-06 | **Home "Heads up" alerts** (bye, injured, questionable, boomed) with photos | No alert applied to the real lineup that day; the logic is unit tested | Fixture lineup with a bye and a questionable starter | Playwright | Open |
| V-07 | **Onboarding screens** (username → leagues → syncing → pick team, pre-selected team, unknown username, no leagues) | Run through the API with `curl`, not through the screens | Click through with a test username | Playwright (Sleeper mocked) | Open |
| V-08 | **Header actions**: league switcher, refresh → "Syncing…" → "League updated", rate-limit message, More menu, sign out | Not clicked in the browser | Click each; refresh twice within a minute for the 429 message | Playwright | Open |
| V-09 | **Settings actions**: change my team, unfollow (confirm dialog), delete account (confirm dialog → signed out, data gone) | Avoided clicking confirm dialogs in the shared browser; the API side is tested | Run each in a throwaway account | Playwright | Open |
| V-10 | **Light theme on every screen** | Only the Matchup screen was seen in light mode | Toggle on each screen; check contrast of chips, range bar, position colors | Playwright screenshots | Open |
| V-11 | **Accuracy page with real grades** (stats, by-position and week tables) | No genuine grades exist yet; only the empty state was seen | After the first week graded from pre-kickoff projections | By hand, then Playwright with fixture grades | Open |
| V-12 | **Real "Sign in with Google"** | No Google OAuth credentials yet | Create a Google OAuth client, sign in on localhost, then on the deployed site | By hand | Waiting on credentials |
| V-13 | **Real magic-link email** through Resend (delivery, spam folder, link works once, 10-minute expiry) | No Resend key yet; locally the link prints in the terminal | Send to a real inbox; reuse the link to confirm it is refused | By hand | Waiting on API key |
| V-14 | **Playwright's browsers under Windows Smart App Control** | Not installed yet | Install Playwright in step 14; fall back to Docker if blocked | Step 14 | Open (backlog P-02) |
| V-15 | **Better Auth after upgrades**: its schema check warns that `user_id` is an integer, harmless today | Can only be checked when Better Auth is upgraded | After each upgrade: `npm run auth:schema` and one sign-in | Each upgrade | Open (backlog P-05) |

## Verified

| ID | What | When | How |
|---|---|---|---|
| (none yet) | | | |

Related: [Improvement Backlog](Improvement-Backlog.md) · [P1 Build Plan](P1-Build-Plan.md) · [UI Screens](../Specs/UI-Screens.md) · [ADR-019 Testing](../Decisions/ADR-019-Testing.md)
