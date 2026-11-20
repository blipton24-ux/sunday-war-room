---
title: "ADR-069: Practice status goes into the chance he plays; injury news is shown, not modelled"
date: 2026-11-20
tags: [adr, model, injuries, data-source, p4]
status: accepted
---
# ADR-069: Practice status goes into the chance he plays; injury news is shown, not modelled

## Context
[ADR-068](ADR-068-P4-Questionable-Players-Projected-If-Playing.md) fitted the chance a Questionable or Doubtful player plays from his status, position and whether he starts. Backlog M-34 asked for an injury news source; M-35 asked for Friday practice status, which changes the chance a lot (Questionable: full practice 75% played, limited 64%, none 41%, 2016-2025).

What each source holds (checked 2026-11-20, Ladd McConkey, Questionable, back):

| Source | Holds | Example |
|---|---|---|
| Sleeper player list (already used) | status and one word | "Questionable", "Spasms"; its practice fields are empty for every player |
| nflverse injury report (already loaded daily) | the official practice report, mid-week, every game since 2016 | "Limited Participation in Practice" (week 11, loaded Thursday) |
| ESPN per-player news (`site.api.espn.com/apis/fantasy/v2/games/ffl/news/players?playerId=`) | short dated Rotowire updates; free, no sign-in, not documented | "McConkey (back) was a limited participant in Thursday's practice" |

M-35 said practice status was not in the live feed; it is, through the daily nflverse refresh.

A model input has to be gradable on 2022-2025 ([ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md)). Practice status is stored for those seasons; news text is not, so its effect on accuracy cannot be measured.

## Options considered

**The same example:** Puka Nacua is Questionable (hamstring), limited Friday; 15.0 half PPR if he plays.

| | **A: practice in the model, news shown** | B: practice only | C: news text in the model too |
|---|---|---|---|
| Chance he plays | from status, position, starter and practice (about 64%) | same | same, plus guesses from wording |
| Screen | "Q · plays ~64% · Limited Fri" and the latest news line | no news line | same as A |
| Measurable on past seasons | yes; news is display only | yes | no |
| New source | ESPN news (undocumented, may change) | none | ESPN news, and its wording becomes an input |

## Decision
**Option A** (owner, 2026-11-20).
- `fit_play_rates` groups by position, status, starter and last practice status (full, limited, did not practice, unknown); a thin group leans on its status-and-practice rate overall. Live and backtest read the same practice code from the feature table (nflverse injury report).
- ESPN's per-player news is shown beside an injured player's projection, never a model input. Fetching, storing and showing it come with the live work in P4 step 10 (M-10, M-34); a failed fetch hides the line and changes no number.

## Why
Practice status is official, already loaded and measurable, and it is the strongest signal found for whether a Questionable player plays. News helps a person decide but cannot be graded, so it informs without moving the numbers.

## Result
The four-season points evaluation cannot see this change: it grades the "if he plays" number, which practice status does not move (2026-11-20 run identical to ADR-068's). The chance he plays was graded directly instead: 1,925 Questionable and Doubtful player-games in 2022-2025, each predicted from earlier seasons only, against whether he took a snap.

| | Without practice (ADR-068) | With practice |
|---|---|---|
| Brier score (lower is better) | 0.2009 | 0.1966 |
| Log loss | 0.576 | 0.565 |
| Seasons better | | 2022, 2023, 2024 (2025 slightly worse) |

95% interval for the Brier change (paired bootstrap over weeks): -0.0091 to +0.0008, so the average gain falls just short of "beyond chance". Questionable players by last practice, played against predicted: did not practice 45% (with practice 40%, without 65%); limited 62% (65%, 64%); full 69% (76%, 61%). **Kept by the owner (2026-11-20)** as an explicit exception to the beats-noise rule: better in three of four seasons and on both scores, and the error for players who did not practice drops from 20 points to 5. Full-practice players are predicted a little high (backlog M-36).

## Trade-offs accepted
The ESPN endpoint is undocumented, like the ESPN scoreboard already used for live scores ([ADR-045](ADR-045-Live-Delivery-Polling.md)); it can change without notice, so the news line is optional. nflverse's practice report lags the teams' release by up to a day; a status that changes after the last refresh is caught by the live status work in step 10.

Related: [ADR-068](ADR-068-P4-Questionable-Players-Projected-If-Playing.md) · [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md)
