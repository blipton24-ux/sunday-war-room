---
title: "P4 Build Plan"
date: 2026-11-12
tags: [build-plan, p4, model]
---
# Phase 4 Build Plan: improved projections

Decisions: [ADR-054](../Decisions/ADR-054-P4-Test-Every-Idea-One-At-A-Time.md) (test one idea at a time) · [ADR-055](../Decisions/ADR-055-P4-Keep-Rule.md) (the keep rule) · [ADR-056](../Decisions/ADR-056-P4-Earlier-Techniques-Ideas-Only.md) (earlier techniques, ideas only) · [ADR-057](../Decisions/ADR-057-P4-Scope-Weekly-Accuracy.md) (scope). Results go in the [Model Experiments](Model-Experiments.md) ledger.

## Progress
**Stage 1 built 2026-11-12** (model still 1.0.0). Results of the checks that gate everything else:
- The upgraded backtest reproduces ADR-034: full PPR, 2025, weeks 5-18, startable players picked by the model's own projection, every game counted: **6.45** (season average 6.50). Half-PPR overall 4.03 matches the committed report.
- `--compare shipped,shipped` shows exactly 0.000 change on every slice.
- Injury rule hand-checked on 14 + 8 + 12 named 2025 games; the first version was wrong and was fixed (see 5a).
- First experiment run through the machinery: E-01 in the [ledger](Model-Experiments.md), dropped.
- 449 backend tests at 99% coverage, 91 web tests, strict mypy clean (run in a Linux container; see backlog P-18).
Stage 2 (the experiments) is next.

## Why
Model 1.0.0 misses by 6.45 points per startable player (held-out 2025, full PPR), against 6.50 for a plain season average and 5.83 for the earlier project's model ([ADR-034](../Decisions/ADR-034-Ship-Model-v1-Upgrade-Later.md)). Today it looks only at **points** (`api/app/model/projection.py`): a recent-weighted average, times one opponent factor and a snap-share factor. It never sees targets, carries, yards or touchdowns separately.

## Stage 1: measuring tools (model stays 1.0.0)
1. **Backtest upgrades (M-09)**: startable-player slice, weeks 1–4 apart from 5+, choice of scoring (half PPR, full PPR, standard).
2. **`--compare`**: two model versions over the same weeks in one table, with a paired bootstrap so noise is labelled noise.
3. **`ModelConfig`**: a frozen dataclass of switches passed into `project_week`. Live code runs the shipped config; only the backtest turns extra switches on.
4. **Raw stats reach the model**: extend the history frame with targets, carries, yards, touchdowns, receptions and attempts. Feature code lives in `api/app/model/features/` as pure functions (history before the week in, one row per player or team out).
5. **Three sets of seasons**: tuning 2022–2024, check 2025, fresh 2026 weeks looked at once per version. (2021 is loaded too, as history for 2022's projections.)
   - **5a. Injury-affected games don't count.** Implemented in `api/app/model/features/injury_games.py`. A game is marked *hurt during* when the player's snap share falls under half his own recent normal (the mean of up to 4 earlier games, normal at least 30%, at least 2 earlier games) **and** there is direct evidence of an injury at his team's next game: an injury-report designation (Out, Doubtful, Questionable) or a reserve-list listing (injured reserve; nflverse weekly rosters, `RES`). *Hurt before* means listed Out or Doubtful and played anyway (a player who did not play has no stat row and is already absent). Questionable players who played are kept and reported as their own line. The report prints "injury games left out" (headline) and "everything counted", with the counts. Both pieces of evidence are known before the next kickoff, so the same marking also serves the experiment of leaving those games out of a player's own history, with no look at anything later.
   - *Hand check, 2025 (before any experiment):* the first version used "missed his next game" as evidence. It flagged two quarterbacks who were benched when the starter returned (Browning, Rattler), because absence cannot tell injury from demotion. Roster status separates them (injured players show `RES`, benched ones stay `ACT`), so the rule now needs the report or reserve evidence. Re-check: Burrow, Skattebo, Wilson, Tracy, Ridley and Harris are marked; Browning, Rattler, Moore (cut) and Campbell (practice squad) are not; 14 more random marks, none clearly wrong. The rule is strict on purpose (backlog M-20). It is now fixed and is not tuned against model results.
   - *Startable picks:* the slice is picked by the plain season average, so two models are graded on the same players; the report also shows it picked by the model's own projection (how ADR-034's table was built).
6. **Past weeks stay visible across versions (M-01)** (done): screens show the frozen row from whichever version froze it, else the current version's (`api/app/services/versions.py`); Accuracy stays per version with `?model_version=` and `available_versions` (UI picker is backlog U-17).
7. **Experiment ledger** ([Model Experiments](Model-Experiments.md)).
8. **Injury and depth-chart snapshots (M-11)** (done): `player_status_snapshots` keeps a row whenever a computed player's injury status or depth-chart slot changed; nflverse's weekly injury reports and reserve lists are stored in `injury_reports` (2021–2026).

## Stage 2: experiments
Loop per idea: write it in the ledger → build behind a switch → compare on tuning seasons → confirm on 2025 → record → keep or drop. Kept ideas are grouped into a numbered version with the fresh-weeks check, refitted ranges (`--write-calibration`), a spec update and a `MODEL_VERSION` bump in the same commit.

- **A. Opportunity (M-02):** target share and carry share; air-yards share and WOPR; red-zone and goal-line share; routes and snap share; expected points per opportunity (nflverse `ff_opportunity`) against our own; touchdown regression; **project the stats, then score them** with the league's own rules (also addresses M-08).
- **B. Defense against each position, run and pass apart:** pass defense (yards and touchdowns allowed to WR, TE, RB receiving, QB), run defense (rushing yards and touchdowns allowed to RB and QB), sacks, interceptions and pressure, adjusted for who each defense has played, last season blended in early, small samples shrunk toward average instead of the hard ±25% limit.
- **C. How good the offense is:** team points, yards, plays, pass rate, pace; the betting market's expected team score (spread and total in the nflverse schedule); game script; QB quality and QB changes; offensive-line pressure and sack rate.
- **D. Role and depth:** depth-chart rank for RB/WR/TE (M-03); teammate out; rookies and no-history players from draft round (M-05); season opener (M-06); trend in snap and target share.
- **E. Injuries:** test the current discounts on past seasons; fresher status near kickoff (M-10, needs a source and timing decision); first games back.
- **F. Game conditions:** home or away, dome, wind and temperature, short weeks, travel.
- **G. Kickers and defenses:** from expected team score, dome, stalled drives; defenses from the opponent's expected score and the opposing QB's sack and turnover rates (M-04).
- **H. How the pieces combine:** per-position half-life and last-season weight; hand-set multipliers against learned weights against a tree model (a learned model ships only if every number is still explainable on the Player screen); a blend of the best two.
- **I. Ranges and win chance:** ranges per scoring format (M-08); wider or narrower ranges by player type; QB and his receivers moving together in the simulation (M-07); weekly auto-refit with the same keep rule (M-14).

Not in P4 ([ADR-057](../Decisions/ADR-057-P4-Scope-Weekly-Accuracy.md)): smarter rest-of-season (M-15), IDP (M-18), keeper and dynasty value.

## Decisions still to make
Each follows [ADR-003](../Decisions/ADR-003-Documentation-Standard.md): injury source and timing (before group E); learned weights against hand-set, if a learned model wins (before shipping group H).

## Verification
- Stage 1: the upgraded backtest reproduces the 1.0.0 numbers (4.03 overall; startable 6.35 / 6.45); `--compare` of a model against itself shows zero difference.
- Injury marking is spot-checked by hand on about 20 known games (real in-game injuries, plus benchings and blowouts that must not be marked) before any experiment uses it. If nflverse injury reports have gaps for a season, marking falls back to "missed the next game" and the report says so.
- Every feature function has unit tests, including one that fails if it reads a game at or after the week being projected.
- Each version: pytest, the fresh-weeks check, the Accuracy page still showing earlier weeks, and the app run locally on a real league to read the new "why this number" factors. CI green before each merge.

Related: [Projection Model](../Specs/Projection-Model.md) · [Backtest Report](Backtest-Report.md) · [Improvement Backlog](Improvement-Backlog.md) · [Later Phases Outline](P2-P8-Outline.md)
