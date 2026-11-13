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
**Stage 2, round 1 done (2026-11-12):** every idea built as a setting, each run alone, then six per-position tuners side by side. RB, WR, TE and DEF beat the shipped model on both sets of seasons (all weeks); QB and K did not hold up on 2025. Results in the [ledger](Model-Experiments.md). The idea code has its unit tests (`api/tests/unit/test_model_ideas.py`, including one that turns every switch on and fails if a game at or after the projected week moves the number).
**Stage 2, round 2 next** ([ADR-058](../Decisions/ADR-058-P4-Round-2-One-Position-At-A-Time.md)): one position at a time (RB, WR, TE, QB, DEF, K), every idea at every strength, the five deferred ideas and ideas specific to each position, a finer tuner, and a review with the owner after each position. See Round 2 below.

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

## Round 2: one position at a time

Decided in [ADR-058](../Decisions/ADR-058-P4-Round-2-One-Position-At-A-Time.md). Round 1's tuners were already per position, but searched shallowly. Round 2, for each position in turn:

1. **Ideas list:** round 1's settings for the position, the deferred ideas (E-04 nflverse expected points, E-14 depth-chart rank, E-15 teammate out, E-20 first games back; E-19 fitted injury discounts gets its own test), and new ideas specific to the position. The owner sees the list before the ideas are built.
2. **Sweep** (`tune.py --stage sweep`): every idea at every strength, alone against the shipped model, tuning seasons only.
3. **Tune** (`--stage tune`): round 1's method, started from the sweep's best values, then a refine step between grid points.
4. **Check** (`--stage check`): 2025 opened once; kept if better beyond chance on all weeks together, on both sets of seasons.
5. **Stop:** results to the ledger and `api/backtest/tuning/<POS>.md`, then a review with the owner before the next position.

Data the new ideas need (depth charts, nflverse expected points, air yards, weekly rosters) is loaded straight from nflverse inside the backtest only; the live app is untouched until something is kept (backlog M-22). Before a version ships, the 2026 weeks played so far get their one look.

**Built 2026-11-13:** the staged tuner (`--stage sweep|tune|check`, `--jobs`, `--settings` to add newly built ideas to an earlier sweep; a re-tune after the check keeps the earlier look on record) and the four deferred ideas as settings (`nfl_xfp_weight`, `depth_rank`, `teammate_out`, `return_discount`), tested in `api/tests/unit/test_round_2.py`. On real data, nflverse expected points cover about 90% of QB/RB/WR/TE games and depth tiers 86-96% in every season. Per-position pages: [Tuning](Tuning/README.md).

## How the tuners work

Built 2026-11-12 after the owner asked for ideas to be kept per position and tuned as far as they will go. Code: `api/app/scripts/tune.py`, settings in `api/app/model/config.py`.

**What a tuner is.** Every idea is a setting with a dial: how much of the projection comes from volume (0%, 25%, 50%...), how many games of memory the average has, how far an opponent can move a number. A tuner is a program that turns each dial for **one position** and keeps the position that gives the smallest average miss. There are six, one each for QB, RB, WR, TE, K and DEF, run side by side.

**One tuner, step by step** (the WR tuner as the example):
1. Start from the shipped model and measure its average miss on startable WRs in the tuning seasons (2022–2024), injury games left out.
2. Take the first setting, say `xfp_weight` (share of the projection from volume). Re-run the three seasons at 0, 0.25, 0.5, 0.75 and 1.0. If the best value beats the current miss by more than **0.004 points**, keep it; otherwise leave the setting alone (a smaller gain is treated as noise).
3. Move to the next setting and do the same, with the earlier winners left in place.
4. After the last setting, start again from the first: a dial's best position can change once the others have moved. Stop when a whole pass changes nothing, or after three passes.
5. Only then open the check season (2025), once. Compare the tuned WR settings with the shipped model on games the tuner never saw.

**What gets shipped.** A position's tuned settings ship only if they beat the shipped model on the tuning seasons **and** on 2025 by more than chance ([ADR-055](../Decisions/ADR-055-P4-Keep-Rule.md)). Each position is judged alone, so WRs can take an idea that QBs reject. Before the version ships, the fresh 2026 weeks get their one look.

| | Tuning seasons 2022–2024 | Check season 2025 | Fresh weeks 2026 |
|---|---|---|---|
| Used to pick a dial position | yes | never | never |
| Used to decide keep or drop | yes | yes | yes, once per version |

**Why it is built this way.** A tuner that tries hundreds of combinations will always find one that looks good on the games it tried them on. The 2025 season is the guard: settings that only memorised 2022–2024 fall apart there. For the same reason a tuner never goes back to adjust a dial after seeing 2025.

**Settings each tuner may turn**

| Setting | What it does | Positions |
|---|---|---|
| `half_life`, `prior_games`, `prior_games_opener` | How fast old games fade; how much last season counts; the same for weeks 1–4 | all |
| `opp_fade_games`, `opp_clamp` | How quickly and how far the opponent moves a projection | all |
| `xfp_weight`, `td_regression` | Share from volume (targets, carries); how much touchdown luck is removed | QB RB WR TE |
| `def_pass`, `def_run`, `def_schedule_adjust` | Opponent rated on its pass defense, its run defense, and adjusted for who it has faced | QB RB WR TE |
| `team_offense`, `implied_total`, `game_script` | Team scoring strength, the betting market's expected score, favourite or underdog | QB RB WR TE |
| `home_boost`, `wind_penalty`, `rest_effect`, `rookie_prior` | Venue, wind, rest days, rookies by draft round | QB RB WR TE (K: venue, wind) |
| `usage_trend`, `role_window`, `role_clamp` | Recent share of targets and carries, or of snaps, against the season | RB WR TE |
| `def_sack_int` | Opponent's sack and interception rate | QB |
| `kicker_model` / `defense_model` | Team's (or the opponent's) expected score | K / DEF |

Kickers and defenses are not part of the startable slice, so their tuners are judged on every game. Tuning uses full-PPR scoring. A per-position setting is written `xfp_weight=0.5@WR`; several are joined with `+`, and `python -m app.scripts.backtest --compare shipped,<settings>` re-checks any combination.

Not in P4 ([ADR-057](../Decisions/ADR-057-P4-Scope-Weekly-Accuracy.md)): smarter rest-of-season (M-15), IDP (M-18), keeper and dynasty value.

## Decisions still to make
Each follows [ADR-003](../Decisions/ADR-003-Documentation-Standard.md): injury source and timing (before group E); learned weights against hand-set, if a learned model wins (before shipping group H).

## Verification
- Stage 1: the upgraded backtest reproduces the 1.0.0 numbers (4.03 overall; startable 6.35 / 6.45); `--compare` of a model against itself shows zero difference.
- Injury marking is spot-checked by hand on about 20 known games (real in-game injuries, plus benchings and blowouts that must not be marked) before any experiment uses it. If nflverse injury reports have gaps for a season, marking falls back to "missed the next game" and the report says so.
- Every feature function has unit tests, including one that fails if it reads a game at or after the week being projected.
- Each version: pytest, the fresh-weeks check, the Accuracy page still showing earlier weeks, and the app run locally on a real league to read the new "why this number" factors. CI green before each merge.

Related: [Projection Model](../Specs/Projection-Model.md) · [Backtest Report](Backtest-Report.md) · [Improvement Backlog](Improvement-Backlog.md) · [Later Phases Outline](P2-P8-Outline.md)
