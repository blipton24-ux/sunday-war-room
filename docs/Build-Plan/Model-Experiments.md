---
title: "Model Experiments"
date: 2026-11-12
tags: [build-plan, model, backtest]
---
# Model experiments (P4)

One row per idea, kept or dropped, with its numbers. Rules: [ADR-054](../Decisions/ADR-054-P4-Test-Every-Idea-One-At-A-Time.md) (how ideas are tested) and [ADR-055](../Decisions/ADR-055-P4-Keep-Rule.md) (when one is kept). Dropped ideas stay here so they are not retried blindly.

Columns: **Tuning** = change in startable-player average miss on 2022–2024 (negative is better), **Check** = the same on 2025, **Worst position** = the biggest loss at any position, **Verdict** = kept, kept for named positions, dropped, or noise.

| ID | Idea | Group | Data needed | Tuning | Check | Worst position | Verdict | Version |
|---|---|---|---|---|---|---|---|---|
| E-00 | Baseline: model 1.0.0 | | | n/a | n/a | n/a | incumbent | 1.0.0 |
| E-01 | Leave injury-spoiled games out of a player's own history (`skip-injury-history`) | E / D | nflverse injury reports, rosters | +0.016 (worse, beyond chance) | -0.002 (noise) | RB +0.020 (tuning) | **dropped** | n/a |

Groups follow the [P4 Build Plan](P4-Build-Plan.md): A opportunity · B defense by position · C offense quality · D role and depth · E injuries · F game conditions · G kickers and defenses · H how pieces combine · I ranges and win chance.

## Notes

**E-01** (2026-11-12, full PPR, startable players, weeks 5+, injury games left out): the idea was that a 2-point game caused by an injury should not drag down a player's later projections. On the tuning seasons (2022-2024) the change was +0.016 points, an interval of +0.001 to +0.031, so slightly worse; on 2025 it was -0.002 (-0.020 to +0.016), noise; no position moved by more than 0.02. A plausible reason: games where a player was hurt are honest evidence that he gets hurt, and dropping them loses information. Not retried unless the injury rule changes.

## Candidate list (planned, 2026-11-12)

Every idea below becomes a switch in `ModelConfig`. All switches are built first, then each is backtested one at a time against the best-so-far (ADR-054), then the code tests run once. Status: **planned** until a row moves into the table above. Data is free nflverse unless noted.

| ID | Switch | Idea | Data | Group |
|---|---|---|---|---|
| E-02 | `xfp-blend` | Blend recent points with expected points from opportunity (targets, carries, air yards, red-zone) at league-average efficiency, fit on earlier seasons only | player stats | A |
| E-03 | `td-regression` | Pull touchdown scoring toward the typical rate for the player's volume | player stats | A |
| E-04 | `ff-opportunity` | Use nflverse's own expected fantasy points per game instead of ours | `load_ff_opportunity` | A |
| E-05 | `usage-trend` | Target share and carry share trend (last 2 games vs season) replaces the snap-share role factor | player stats | A |
| E-06 | `def-pass-position` | Opponent factor for QB, WR, TE and receiving RB from passing and receiving yards and touchdowns allowed to that position | player stats by opponent | B |
| E-07 | `def-run-position` | Opponent factor for RB and QB runs from rushing yards and touchdowns allowed | player stats by opponent | B |
| E-08 | `def-sack-int` | QB factor from the opponent's sack and interception rates | team stats | B |
| E-09 | `def-schedule-adjust` | Adjust each defense's numbers for the offenses it has faced | player stats | B |
| E-10 | `opp-shrink` | Replace the hard ±25% opponent clamp with shrinkage by games played | none | B |
| E-11 | `team-offense` | Team points and plays per game (trailing) scales every player on the team | team stats | C |
| E-12 | `implied-total` | Team's implied score from the betting spread and total | schedules | C |
| E-13 | `game-script` | Favourites run more and underdogs pass more, from the spread | schedules | C |
| E-14 | `depth-rank` | Depth-chart rank adjustment for RB, WR, TE | `load_depth_charts` | D |
| E-15 | `teammate-out` | Raise a player when a higher-ranked teammate at his position is Out | injuries, depth charts | D |
| E-16 | `rookie-prior` | Starting value for players with no history from draft round and pick | `load_draft_picks` | D |
| E-17 | `opener-weights` | Last-season blend weight tuned for weeks 1-4 | none | D |
| E-18 | `role-window` | Role factor window and clamp tuned per position | none | D |
| E-19 | `injury-discount-fit` | Replace the guessed Questionable and Doubtful multipliers with ones fit on past seasons | injury reports | E |
| E-20 | `return-from-injury` | Reduced workload in the first games back from a reserve-list stay | rosters, injuries | E |
| E-21 | `home-away` | Home or away | schedules | F |
| E-22 | `roof-weather` | Dome, wind and temperature | schedules | F |
| E-23 | `rest-days` | Short weeks and extra rest | schedules | F |
| E-24 | `kicker-model` | Kickers from the team's implied total and dome | schedules | G |
| E-25 | `defense-model` | Defenses from the opponent's implied total and sack and turnover rates | schedules, team stats | G |
| E-26 | `halflife-by-position` | Recency half-life tuned per position | none | H |
| E-27 | `prior-games-by-position` | Last-season weight tuned per position | none | H |
| E-28 | `learned-weights` | A ridge regression combines the features instead of hand-set multipliers | all of the above | H |
| E-29 | `tree-model` | A gradient-boosted model on the same features, compared for accuracy and explainability | all of the above | H |
| E-30 | `blend-best` | A blend of the best hand-set and the best learned model | winners | H |
| E-31 | `ranges-by-format` | Ranges fitted per scoring format | backtest | I |
| E-32 | `player-type-ranges` | Wider ranges for boom-or-bust players | backtest | I |
| E-33 | `correlated-sim` | A quarterback and his receivers move together in the simulation | backtest | I |

Not planned: quarterback-change effects (covered by E-11 and E-12), routes run and pressure rates (no free per-game source found).

Related: [P4 Build Plan](P4-Build-Plan.md) · [Backtest Report](Backtest-Report.md) · [Improvement Backlog](Improvement-Backlog.md)
