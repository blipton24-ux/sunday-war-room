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
| V-01 | **Every screen on a real phone.** Phone-sized layout, touch targets and overflow are now tested at 390 and 360 px in an emulated iPhone (V-P12). Not covered: a real device's safe areas, real touch, Safari. | Emulation isn't a device | One look on a real phone, in both themes | By hand, real phone | Open (backlog U-09) |
| V-03 | **"Projected final" while games are live** can read below the live score | Known behavior, not a test gap: players in progress keep their pre-game projection. The real fix needs live scores (P2) | During a live game, compare the header's projected final with the score; re-check after the P2 live work | Sunday, by hand | Open (backlog U-07) |

## Also not yet seen working

| ID | What isn't verified | Why not | How to test | Where | Status |
|---|---|---|---|---|---|
| V-11 | **Accuracy page with real grades.** Fixture grades are tested (V-P12). Not yet seen: grades from genuinely pre-kickoff projections during a real week. | No genuine grades exist yet | After the first real week is graded | By hand | Open |
| V-12 | **Real "Sign in with Google"** | No Google OAuth credentials yet | Create a Google OAuth client, sign in on localhost, then on the deployed site | By hand | Waiting on credentials |
| V-13 | **Real magic-link email** through Resend (delivery, spam folder, link works once, 10-minute expiry) | No Resend key yet; locally the link prints in the terminal | Send to a real inbox; reuse the link to confirm it is refused | By hand | Waiting on API key |
| V-15 | **Better Auth after upgrades**: its schema check warns that `user_id` is an integer, harmless today | Can only be checked when Better Auth is upgraded | After each upgrade: `npm run auth:schema` and one sign-in | Each upgrade | Open (backlog P-05) |

## Not yet seen working: the installed app (P1 step 12, 2026-11-09)

| ID | What isn't verified | Why not | How to test | Where | Status |
|---|---|---|---|---|---|
| V-16 | **Installing on Android**: Install button → Chrome's dialog → icon on the home screen → opens full screen. Also: the maskable icon's crop looks right (circle and squircle), and long-pressing the icon shows the Lineup and Matchup shortcuts. | Needs a phone. In desktop Chrome the button appeared (Chrome considered the app installable), but the install itself wasn't completed. | Install on an Android phone against the deployed site | By hand, real phone | Open |
| V-17 | **Installing on iPhone**: Share → Add to Home Screen, the icon (apple-icon), the "Installed" card. Also the full-screen layout: the header isn't hidden under the status bar or notch (safe-area padding), and the bottom tabs clear the home indicator. | Needs an iPhone. Desktop layout was measured unchanged, but safe areas are 0 there. | Install on an iPhone; check the top and bottom edges in both themes | By hand, real iPhone | Open |
| V-18 | **Signing in inside the installed iPhone app.** A magic link opens in Safari; the installed app may not share that sign-in. | Needs an iPhone. This is a suspected iOS behavior, not a confirmed bug. | Install, sign out, request a link from inside the app, tap it in Mail | By hand, real iPhone | Open (backlog P-07) |
| V-19 | **A new version reaching installed users.** The worker takes over right away (`skipWaiting` + `clients.claim`), which is safe for content-hashed files, but no update has happened yet. | Only one version exists | After the second deploy, open the app on a device that has the first version | By hand, after step 16 | Open |
| V-20 | **Bad-signal behavior.** Offline (no connection) is tested in a real browser (V-P12). Not tested: a very slow connection where a request neither succeeds nor fails, and airplane mode on a phone. | Playwright offline mode only fails requests | Throttle to a very slow connection; airplane mode | By hand | Open |
| V-22 | **Installing from desktop Chrome or Edge**: the app opens in its own window with no browser bars. | Not completed | Click Install in Settings on a laptop | By hand | Open |

## Not yet seen working: the containers (P1 step 13, 2026-11-09)

| ID | What isn't verified | Why not | How to test | Where | Status |
|---|---|---|---|---|---|
| V-23 | **Images on other processors** (Apple Silicon, ARM servers). Only built and run on this PC's x86 Docker. | One machine | Build and run on an ARM machine, or build multi-platform in CI; check what the hosting platform builds | CI / hosting platform | Open |
| V-25 | **Restart and recovery**: stopping and restarting the stack keeps data (the `db-data` volume) and the worker resumes; a worker or api crash restarts under the hosting platform's rules. | Only a clean first start was tried | `docker compose down` then `up` (without `-v`); kill the worker mid-sync | By hand; hosting platform (P8) | Open |
| V-26 | **Production settings**: the images with real secrets, a public HTTPS address, a real Resend key and Google OAuth. Locally everything ran with development secrets on `localhost`. | No domain or credentials yet | Deploy (P8) and sign in with both methods | Deploy | Open |
| V-27 | **The container browser experience**: pages were fetched with `curl` and a browser earlier against the non-container build, but the container's `localhost:3000` site wasn't opened in a browser. | Efficiency; same code | Open it once in a browser after `docker compose up` | By hand | Open |

## Added in step 14 (2026-11-09)

| ID | What isn't verified | Why not | How to test | Where | Status |
|---|---|---|---|---|---|
| V-28 | **Safari / WebKit.** The end-to-end suite runs in Chromium only; every iPhone browser uses WebKit. | Not in the suite yet | Add a WebKit project in CI (backlog P-14) and look on an iPhone | CI + real iPhone | Open |
| V-29 | **Keyboard-only and screen-reader use.** Axe checks about a third of accessibility problems automatically ([ADR-041](../Decisions/ADR-041-Accessibility-Standard.md)). | Needs a person | Tab through every screen; listen with VoiceOver or NVDA | By hand | Open |
| V-30 | **Rate limits behind a real proxy.** Better Auth limits sign-in links per IP; behind the hosting proxy every visitor may look like one address unless it reads the forwarded-IP header (backlog P-13). | Only tested on localhost | Request several links from different networks on the deployed site | Deploy (P8) | Open |

## Added in step 15 (2026-11-09)

| ID | What isn't verified | Why not | How to test | Where | Status |
|---|---|---|---|---|---|

## Added in P2 (2026-11-09)

| ID | What isn't verified | Why not | How to test | Where | Status |
|---|---|---|---|---|---|
| V-33 | **Sleeper's codes and transactions against a real league.** The transactions fixture is hand-written in the shape documented at docs.sleeper.com, and three code meanings are assumed: `waiver_type` 0/1/2 = rolling / reverse standings / FAAB; `waiver_day_of_week` 0 = Monday; `trade_deadline` is a week number. The raw values are stored so a wrong mapping can be corrected without re-syncing history. | No real league's transactions recorded | Sync a real league with known settings (priority with a claim window, and a FAAB league) and compare with what Sleeper's app shows | By hand, real league | Open |
| V-34 | **Waiver times and bid guide on a real league.** "On waivers until about …" is the drop time plus the league's claim days; platforms actually run waivers at a set hour (and Sleeper may also lock players whose game has started). The FAAB bid guide (5% of what's left per point a week added, capped at 60%) has not been compared with real bids. | Demo data only | Compare with Sleeper's app for a few dropped players; look at a league's past winning bids | By hand, real league | Open |
| V-35 | **A real NFL Sunday.** The live tick has run only against a fake scoreboard and recorded Sleeper data; ESPN's in-progress format is derived from its scheduled/final format (no game was live when it was recorded). Unchecked: how quickly Sleeper updates matchup points mid-game, ESPN's halftime/overtime/delay states, and that the worker's one-minute cadence keeps up with every followed league. | Built on a Tuesday | Run the stack during a Sunday window with a real league: watch the worker log and the Matchup screen for a few games; record a live scoreboard response as a new fixture | By hand, real Sunday | Open |

## Added in P3 (2026-11-10)

Everything ESPN-shaped was written from earlier knowledge of the API and tested on **synthetic, scrubbed responses** (`api/tests/espn_fixtures.py`); no real ESPN response has been recorded yet. P3 step 15 (the owner's real private league) is where these are proven.

| ID | What isn't verified | Why not | How to test | Where | Status |
|---|---|---|---|---|---|
| V-36 | **ESPN's real response shapes.** Field names and nesting for the league, teams, rosters, matchups (`appliedStatTotal`, `pointsByScoringPeriod`, `rosterForCurrentScoringPeriod`), transactions (`mTransactions2`) and the fan profile; the lineup slot ids; ESPN's numeric team ids (`proTeamId`) and the D/ST id rule `-(16000 + proTeamId)`; whether `mBoxscore` + `scoringPeriodId` returns what the matchup mapping expects. A wrong guess fails loudly (schema error), not silently. | No real ESPN response recorded | Run `connect`, then a sync, on the owner's private league; scrub and commit a recorded copy as a new fixture | Real league (P3 step 15) | Open |
| V-37 | **Our scores against ESPN's own.** The scoring map (step and bonus shapes, per-position values, open-ended field-goal ladders, touchdown groups, `YA399` = 350-399) is from earlier work. The "last field-goal band covers longer kicks" rule and the touchdown-group rule are the least certain. | No real finished week to compare | For one finished week, score every starter with our rules and compare with ESPN's per-player totals (golden test, within 0.01); record gaps in the Backtest Report | Real league (P3 step 15) | Open |
| V-38 | **How ESPN answers expired cookies.** We treat 401/403 with cookies as "refused" and a 404 from the fan profile as "not signed in". ESPN might redirect, return 200 with an anonymous profile, or behave differently for `espn_s2` (expired) vs `SWID` (wrong). | Can't expire a real cookie on demand | Sign out of ESPN, then sync with the saved cookies; check the status flips to "needs reconnect" | By hand | Open |
| V-39 | **The cookie guide in each browser.** The steps for Chrome, Edge, Firefox and Safari and the picture (a schematic, not a screenshot) were written from memory of each browser's developer tools; menu names change. Rewritten in more detail 2026-11-12 after the owner followed them in Edge on Windows: there the Application tab was behind the **+** (add a tool), not the » overflow, so the Edge steps now say so. Only that one Edge run has been seen; Chrome, Firefox and Safari wording, and other Edge versions, are unchecked. Browsers we don't recognise get the Chrome steps as a best guess. Whether `espn_s2` should be pasted URL-encoded (as browsers store it) or decoded is untested against ESPN. | Not followed against live ESPN | Follow the guide in each browser with a real account; connect | By hand, 4 browsers | Open |
| V-40 | **"Email me a link" through Resend.** Built and tested (a locally logged link), but a real send needs a Resend key and, off this machine, a verified domain. | No domain until P8 | Send to the owner's own address with a real key | By hand | Open |
| V-41 | **Waivers, trades, lineup and live on an ESPN league.** Sync is tested end to end on ESPN data, but the feature screens have not been exercised on an ESPN league (the synthetic roster mostly has players our list doesn't know). Also unchecked: how many real ESPN players fail to match and fall to the name fallback or stay unmapped (`unmapped_players` in the sync log). | Needs a real roster | Use every screen on the owner's league; read the sync log's unmapped list | Real league (P3 step 15) | Open |
| V-43 | **The scheduled nflverse job with the new downloads.** The ingest now also fetches weekly injury reports and weekly rosters (reserve lists). The ingest function was run by hand against real nflverse for 2021-2026 (58,151 injury rows) and its tests pass, but the worker's own daily run hasn't been watched with them. | The daily job runs at its own time | After the next scheduled run, check `injury_reports` has the current week and the job log shows `injury_reports=` | Worker log, `injury_reports` table | Open |
| V-42 | **ESPN rate limits and blocking.** The client retries 429/5xx politely and polls only during game windows, but ESPN's real limits for a shared server address are unknown. | Unofficial API | Watch the worker log for 429s over a real Sunday; see V-35 | Real Sunday | Open |

## Added in P4 (2026-11-13)

| ID | What isn't verified | Why not | How to test | Where | Status |
|---|---|---|---|---|---|
| V-44 | **Model 1.1.0 on the screens.** The stored week 10 projections were checked in the database (four running backs, three leagues, matching the hand-run numbers exactly), but no screen was opened: the Player screen's new factors (betting market, carry volume, first game back) and the Accuracy page with two versions for one week. | Shipped from the terminal | Open a running back on the Player screen and read the factors; after week 10 is graded, switch Accuracy between 1.0.0 and 1.1.0 | Browser | Open |
| V-45 | **Betting lines kept fresh by the daily ingest.** The lines were back-filled by hand for 2021-2026 (all games to week 10 of 2026 have one); the scheduled job now writes them too, but its run has not been watched. Lines move during the week, so a projection uses whatever was stored at its last compute. | The daily job runs at its own time | After the next 10:00 UTC run, check `nfl_games.spread_line` for next week's games | Worker log, `nfl_games` | Open |

## Verified

| ID | What | When | How |
|---|---|---|---|
| V-P1 | Service worker registers, activates and controls the page in real Chrome (production build) | 2026-11-09 | Chrome: scope `/`, `activated`, controlling |
| V-P2 | Chrome treats the app as installable: the Install button appeared in Settings | 2026-11-09 | Chrome fired `beforeinstallprompt` |
| V-P3 | The worker stores only fixed files: after visiting Lineup, Matchup and Settings it held 20 font/CSS/JS files and its 3 precached files, no `/api` entries, no pages | 2026-11-09 | Inspected Cache Storage in Chrome |
| V-P4 | With the web server stopped, loading `/lineup` shows the offline page; after restarting, "Try again" loads the real page | 2026-11-09 | Chrome, server stopped and restarted |
| V-P5 | Manifest, icons, `apple-icon`, SVG favicon, install tags and the `sw.js` no-cache header are served correctly | 2026-11-09 | `curl` against the production build |
| V-P6 | The desktop header and tab bar are unchanged by the iPhone safe-area padding | 2026-11-09 | Measured in Chrome: padding 0, header 62 px, nav offset 61 px | |
| V-P7 | `docker compose up` from nothing: migrate runs and exits, api and web become healthy, worker starts. All four migrations ran clean on an empty database. | 2026-11-09 | A separate compose project with its own empty volume |
| V-P8 | First start loads NFL history by itself (queued by the worker, 5 seasons, 9 seconds) | 2026-11-09 | Worker log in the test stack |
| V-P9 | Sign-in, connecting Sleeper, syncing, picking a team and loading every screen work inside the containers; photos served through the image cache (3.7 KB, one-week cache header) | 2026-11-09 | `curl` against the stack |
| V-P10 | A container set up like a public site but using development secrets refuses to run sign-in (HTTP 500 with a clear message); the health check still answers | 2026-11-09 | One-off container |
| V-P11 | All 130 backend tests pass inside the image using exactly the locked package versions, against a real database and Redis | 2026-11-09 | `--target test` image on the stack's network |
| V-P12 | Step 14 end-to-end suite, 62 tests in Edge against the full container stack with a seeded league: first-run onboarding (V-07), every screen with live, bye, questionable and boom states, swaps and alerts (V-02, V-04, V-05, V-06), fixture grades (V-11), phone size at 390 and 360 px with 44 px touch targets (V-01), both themes scanned by axe with no serious findings (V-10), header and Settings actions including unfollow and delete account (V-08, V-09), isolation between users, service worker, offline page and install card (V-20, V-21) | 2026-11-09 | `npm run e2e` in `web/` |
| V-P13 | Playwright runs under Windows Smart App Control using the installed Edge (V-14) | 2026-11-09 | `PW_CHANNEL=msedge` |
| V-C1 | CI passes on a GitHub runner from a clean state: lint, types, OpenAPI and client checks, 160 backend tests at 99% coverage, 71 web tests, both images build (3 min 48 s), 62 Playwright tests in Chromium (full stack build and tests, 5 min); whole run about 6.5 min | 2026-11-09 | GitHub Actions run 42716212296 on `main` |

Related: [Improvement Backlog](Improvement-Backlog.md) · [P1 Build Plan](P1-Build-Plan.md) · [UI Screens](../Specs/UI-Screens.md) · [ADR-019 Testing](../Decisions/ADR-019-Testing.md)
