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

## Round 1, 2026-11-12: each idea alone

Every built switch at one or two hand-picked strengths, each against the shipped model: `python -m app.scripts.backtest --sweep all --scoring full`. Change in average miss in points (negative is better) with its 95% interval, startable players, injury games left out, best first. **Keep rule** is ADR-055 applied to the idea at that one strength for all positions together.

| Idea | Tuning 5+ | Check 5+ | Tuning wk 1-4 | Check wk 1-4 | Worst position | Keep rule |
|---|---|---|---|---|---|---|
| `xfp-blend` | -0.028 (-0.067 to +0.012) noise | -0.081 (-0.129 to -0.032) better | -0.081 (-0.142 to -0.018) better | -0.196 (-0.237 to -0.152) better | QB +0.059 | no |
| `td-regression` | -0.031 (-0.056 to -0.008) better | -0.059 (-0.087 to -0.025) better | -0.076 (-0.119 to -0.033) better | -0.144 (-0.175 to -0.113) better | QB +0.024 | **kept** |
| `td-regression-full` | -0.013 (-0.060 to +0.033) noise | -0.073 (-0.127 to -0.007) better | -0.100 (-0.178 to -0.022) better | -0.212 (-0.248 to -0.172) better | QB +0.169 | no |
| `xfp-blend-25` | -0.028 (-0.048 to -0.008) better | -0.055 (-0.079 to -0.029) better | -0.051 (-0.083 to -0.018) better | -0.119 (-0.150 to -0.091) better | QB -0.002 | **kept** |
| `xfp-blend-75` | +0.001 (-0.057 to +0.061) noise | -0.083 (-0.152 to -0.012) better | -0.084 (-0.171 to +0.004) noise | -0.251 (-0.300 to -0.202) better | QB +0.168 | no |
| `opp-shrink-soft` | -0.007 (-0.019 to +0.006) noise | -0.020 (-0.039 to -0.001) better | -0.007 (-0.027 to +0.011) noise | -0.043 (-0.068 to -0.016) better | TE +0.003 | no |
| `def-pass-position` | +0.002 (-0.011 to +0.015) noise | -0.021 (-0.045 to +0.004) noise | +0.002 (-0.014 to +0.018) noise | -0.002 (-0.017 to +0.010) noise | QB +0.042 | no |
| `halflife-10` | -0.017 (-0.033 to -0.001) better | -0.001 (-0.028 to +0.027) noise | -0.004 (-0.010 to +0.001) noise | -0.009 (-0.022 to +0.000) noise | WR +0.023 | no |
| `halflife-6` | -0.013 (-0.023 to -0.004) better | -0.005 (-0.019 to +0.010) noise | -0.002 (-0.005 to +0.001) noise | -0.005 (-0.013 to +0.000) noise | WR +0.006 | no |
| `roof-weather` | -0.002 (-0.007 to +0.003) noise | -0.011 (-0.026 to +0.000) noise | -0.005 (-0.013 to +0.000) noise | +0.000 (+0.000 to +0.001) noise | WR +0.001 | no |
| `opp-shrink` | -0.002 (-0.010 to +0.007) noise | -0.011 (-0.023 to +0.001) noise | -0.005 (-0.017 to +0.006) noise | -0.029 (-0.045 to -0.010) better | TE +0.011 | no |
| `home-away` | -0.007 (-0.020 to +0.006) noise | -0.000 (-0.028 to +0.027) noise | -0.001 (-0.028 to +0.024) noise | +0.008 (-0.010 to +0.038) noise | TE +0.032 | no |
| `rookie-prior` | +0.000 (+0.000 to +0.000) noise | +0.000 (+0.000 to +0.000) noise | +0.000 (+0.000 to +0.000) noise | +0.000 (+0.000 to +0.000) noise | QB +0.000 | no |
| `opener-weights` | +0.000 (+0.000 to +0.000) noise | +0.000 (+0.000 to +0.000) noise | +0.012 (-0.032 to +0.054) noise | +0.082 (+0.007 to +0.176) worse | QB +0.000 | no |
| `opener-weights-low` | +0.000 (+0.000 to +0.000) noise | +0.000 (+0.000 to +0.000) noise | +0.073 (+0.026 to +0.134) worse | +0.003 (-0.086 to +0.089) noise | QB +0.000 | no |
| `kicker-model` | +0.000 (+0.000 to +0.000) noise | +0.000 (+0.000 to +0.000) noise | +0.000 (+0.000 to +0.000) noise | +0.000 (+0.000 to +0.000) noise | QB +0.000 | no |
| `defense-model` | +0.000 (+0.000 to +0.000) noise | +0.000 (+0.000 to +0.000) noise | +0.000 (+0.000 to +0.000) noise | +0.000 (+0.000 to +0.000) noise | QB +0.000 | no |
| `prior-games-5` | +0.011 (-0.006 to +0.028) noise | -0.004 (-0.027 to +0.022) noise | +0.003 (-0.032 to +0.033) noise | +0.055 (-0.001 to +0.125) noise | QB +0.080 | no |
| `role-window` | +0.009 (-0.012 to +0.031) noise | +0.008 (-0.025 to +0.041) noise | +0.012 (-0.007 to +0.040) noise | -0.018 (-0.056 to +0.000) noise | RB +0.084 | no |
| `rest-days` | +0.008 (+0.003 to +0.013) worse | +0.011 (-0.000 to +0.022) noise | +0.004 (-0.004 to +0.013) noise | +0.002 (-0.005 to +0.008) noise | QB +0.030 | no |
| `game-script` | +0.021 (+0.005 to +0.037) worse | +0.004 (-0.025 to +0.033) noise | -0.018 (-0.053 to +0.021) noise | +0.032 (+0.017 to +0.048) worse | QB +0.045 | no |
| `def-sack-int` | +0.017 (+0.004 to +0.030) worse | +0.015 (-0.002 to +0.030) noise | -0.003 (-0.024 to +0.021) noise | +0.045 (+0.008 to +0.081) worse | QB +0.115 | no |
| `halflife-3` | +0.022 (+0.013 to +0.032) worse | +0.014 (+0.000 to +0.028) worse | +0.002 (-0.001 to +0.006) noise | +0.006 (+0.000 to +0.015) noise | TE +0.034 | no |
| `def-run-position` | +0.010 (-0.012 to +0.032) noise | +0.027 (+0.006 to +0.047) worse | +0.015 (+0.001 to +0.035) worse | +0.016 (-0.018 to +0.049) noise | QB +0.100 | no |
| `implied-total-30` | +0.011 (-0.012 to +0.034) noise | +0.032 (-0.010 to +0.074) noise | -0.026 (-0.069 to +0.017) noise | +0.110 (+0.086 to +0.136) worse | QB +0.104 | no |
| `prior-games-2` | +0.018 (+0.006 to +0.030) worse | +0.025 (+0.007 to +0.042) worse | +0.031 (+0.007 to +0.068) worse | -0.008 (-0.060 to +0.037) noise | TE +0.053 | no |
| `team-offense-25` | +0.038 (+0.017 to +0.061) worse | +0.061 (+0.036 to +0.088) worse | +0.040 (+0.008 to +0.073) worse | +0.132 (+0.079 to +0.190) worse | QB +0.116 | no |
| `halflife-2` | +0.077 (+0.050 to +0.106) worse | +0.068 (+0.031 to +0.104) worse | +0.007 (-0.002 to +0.018) noise | +0.018 (+0.000 to +0.044) noise | TE +0.110 | no |
| `usage-trend` | +0.059 (+0.021 to +0.099) worse | +0.094 (+0.028 to +0.165) worse | +0.037 (-0.004 to +0.097) noise | +0.005 (+0.000 to +0.014) noise | RB +0.125 | no |
| `prior-games-1` | +0.076 (+0.049 to +0.105) worse | +0.079 (+0.040 to +0.115) worse | +0.160 (+0.075 to +0.256) worse | +0.054 (-0.090 to +0.217) noise | TE +0.158 | no |
| `def-schedule-adjust` | +0.110 (+0.068 to +0.152) worse | +0.048 (-0.025 to +0.121) noise | +0.033 (+0.012 to +0.057) worse | -0.027 (-0.087 to +0.012) noise | WR +0.165 | no |
| `implied-total` | +0.078 (+0.031 to +0.125) worse | +0.115 (+0.028 to +0.200) worse | -0.017 (-0.105 to +0.070) noise | +0.273 (+0.233 to +0.326) worse | QB +0.315 | no |
| `team-offense` | +0.122 (+0.079 to +0.167) worse | +0.154 (+0.099 to +0.211) worse | +0.123 (+0.053 to +0.191) worse | +0.307 (+0.207 to +0.432) worse | QB +0.282 | no |

What it shows:
- **Opportunity ideas carry the gain.** A quarter of the projection from volume (`xfp-blend-25`) and half of touchdown luck removed (`td-regression`) pass the keep rule on their own. Stronger doses help more in weeks 1-4 and on 2025 but cost quarterbacks up to 0.17 points, which is why strength is tuned per position below.
- **Team-level multipliers hurt at these strengths** (`team-offense`, `implied-total`, `def-schedule-adjust`, `usage-trend`): a plausible reason is that a player's own recent points already contain most of what his team's scoring says, so multiplying again counts it twice.
- **Zero rows are expected, not broken:** `kicker-model` and `defense-model` only touch K and DEF, which are outside the startable slice (they are judged in their own tuners below); `rookie-prior` only touches players with no history, who are almost never among a week's startable picks by season average; `opener-weights` only touches weeks 1-4.
- These rows are a first look at single strengths, all positions graded together. The verdict per idea and position comes from the tuners below, and from round 2.

## Round 1, 2026-11-12: per-position tuners (full PPR, injury games left out)

Six tuners ran side by side, one per position; how they work: [P4 Build Plan](P4-Build-Plan.md#how-the-tuners-work).

**Per-position tuning** (`app/scripts/tune.py`; all weeks; startable players, every game for K and DEF). Change in average miss with the 95% interval:

| Position | Tuned settings | Tuning | Check 2025 | Both beyond chance? |
|---|---|---|---|---|
| TE | half-life 14, no opponent factor, volume 75%, implied total 30%, role window 3, wind | -0.228 (-0.322 to -0.131) | -0.286 (-0.522 to -0.034) | **yes** (also on weeks 5+; and without wind: -0.203 / -0.293 on weeks 5+) |
| WR | half-life 14, opponent fade 16 and limit 15%, volume 50%, touchdown regression 100%, team offense 25%, implied total 30%, game script, home 4%, no role factor | -0.215 (-0.293 to -0.138) | -0.167 (-0.324 to -0.011) | **yes** on all weeks; weeks 5+ check is -0.107, noise |
| RB | opponent fade 8, volume 25%, touchdown regression 50%, pass defense, implied total 60% | -0.080 (-0.143 to -0.012) | -0.169 (-0.257 to -0.072) | **yes** on all weeks; weeks 5+ tuning is -0.075, noise |
| DEF | last season counts like 8 games, opponent limit 40% | -0.042 (-0.079 to -0.003) | -0.082 (-0.149 to -0.011) | **yes** on all weeks; weeks 5+ noise on both |
| QB | half-life 14, last season 1 game, opponent fade 16, volume 50%, run defense, implied total 30%, home 2%, wind | -0.219 (-0.357 to -0.084) | -0.122 (-0.287 to +0.034) | no: check is noise (266 games) |
| K | half-life 14, last season 8 games, no opponent factor, team implied score 30%, wind | -0.112 (-0.157 to -0.066) | -0.030 (-0.095 to +0.037) | no: check is noise |

RB + WR + TE + DEF together (QB and K left on 1.0.0): startable players, weeks 5+, **6.163 → 6.033** on the tuning seasons and **6.315 → 6.166** on 2025; weeks 1–4, 6.353 → 6.192 and 5.814 → 5.611. The combined run reproduces each tuner's per-position numbers exactly.

**K** (2026-11-12): five settings moved and the tuning seasons improved by 0.11 points, but 2025 kept only 0.03 of it. This is the pattern the check season exists to catch: five dials turned on 1,631 kicker games fit those games. The direction is the same in both sets (longer memory, no opponent factor, a little of the team's expected score), so it is worth retrying with fewer dials or more seasons.

**DEF** (2026-11-12): two changes, both in the direction of trusting a defense's longer record more (last season counts like 8 games instead of 3) and letting the opponent move the number further (up to 40%). `defense_model` (the opposing team's expected score) was tried at every strength and never beat the 0.004 threshold.

Notes:
- Ideas that failed as a blanket rule (implied total, team offense, game script, pass defense) were picked by some position tuners at a lower strength alongside the volume blend. They are judged as part of that position's package, on the check season.
- Wind is the wind recorded for the game, not a forecast (backlog M-21), so it should not ship as tuned. TE holds without it; QB and K did not pass anyway.
- Every setting that reads betting lines, venue or team strength needs the live compute to load that data first (backlog M-22). Nothing here is shipped; `SHIPPED` is unchanged and the model is still 1.0.0.
- The fresh 2026 weeks have not been looked at.

## Round 2, 2026-11-13: one position at a time

Method: [ADR-058](../Decisions/ADR-058-P4-Round-2-One-Position-At-A-Time.md). Each position's numbers are on its own page under [Tuning](Tuning/README.md); this section says what they mean and what was decided. Kept means better beyond chance on all weeks together, on 2022-2024 and on 2025. 2025 was already looked at once in round 1, so a round 2 pass on 2025 is a second look; the 2026 weeks are the final check before anything ships.

### RB (owner review pending)

**Sweep** (each setting alone, 2022-2024; [RB page](Tuning/RB.md)): no single idea moved running backs much. The best were touchdown luck at 25% (-0.017, beyond chance) and 50% (-0.021, noise). The three RB ideas the owner approved did not help alone: receiving points with their own memory -0.004 (noise), yards-per-carry luck +0.003 or worse, carry share x expected team carries +0.016 or worse. The depth-chart tier idea hurt at every strength (+0.013 at 10%, +0.15 at full); a likely reason is that a back listed first in a committee does not get a true starter's points, so a whole-tier move overshoots.

**Tune** (combined, 2022-2024): 5.9212 to **5.8276**. Six settings moved:

| Setting | Shipped | Tuned | Plain meaning |
|---|---|---|---|
| `td_regression` | 0 | 0.5 | Half of a back's touchdown luck is taken out of his history |
| `implied_total` | 0 | 0.3 | 30% weight on the betting market's expected score for his team |
| `opp_clamp` | 0.25 | 0.15 | The opponent can move a projection by at most 15%, not 25% |
| `return_discount` | 0 | 0.2 | 20% lower in his first game back from a reserve list (the top of the grid; higher was not tried) |
| `role_clamp` | 0.15 | 0.075 | The snap-share trend can move a projection by at most 7.5% |
| `carry_volume` | 0 | 0.125 | A light touch of his carry-share trend and his team's expected carries |

**Check:**

| RB, startable, injury games left out | All weeks | Weeks 5+ | Weeks 1-4 |
|---|---|---|---|
| Tuning 2022-2024 | **-0.094** (-0.146 to -0.043) better | -0.101 better | -0.072 better |
| Check 2025 | **-0.161** (-0.214 to -0.107) better | -0.172 better | -0.120 better |

**Passes the keep rule**, on every slice. Against round 1's RB settings (tuning -0.080, check -0.169 on all weeks): about the same on 2025, but now better beyond chance on weeks 5+ of 2022-2024 too, where round 1 was noise. Two ideas that alone did nothing or harm (carry volume, a tighter role factor) earned a small place next to the others; together the package is what helped, as the owner expected.

Re-checked with `python -m app.scripts.backtest --compare shipped,<RB settings>`: the same numbers (RB weeks 5+ -0.101 and -0.172), and exactly 0.000 at QB, WR and TE, so the settings touch running backs only. All startable players together, weeks 5+: -0.035 on 2022-2024 and -0.061 on 2025.

Before shipping: the 2026 weeks; the betting-market and reserve-list settings need their data loaded live (backlog M-22); `return_discount` sits at the top of its grid, so a stronger value is worth a look in a later pass.

## Candidate list (planned, 2026-11-12)

Every idea below becomes a switch in `ModelConfig`. All switches are built first, then each is backtested one at a time against the best-so-far (ADR-054), then the code tests run once. Status: **built** means the switch exists and is in the sweep; **deferred** has a reason. A row moves into the results table above once it has been judged. Data is free nflverse unless noted.

| ID | Switch | Idea | Data | Group |
|---|---|---|---|---|
| E-02 | `xfp-blend` | Blend recent points with expected points from opportunity (targets, carries, air yards, red-zone) at league-average efficiency, fit on earlier seasons only | player stats | A |
| E-03 | `td-regression` | Pull touchdown scoring toward the typical rate for the player's volume | player stats | A |
| E-04 | `ff-opportunity` | Use nflverse's own expected fantasy points per game instead of ours | `load_ff_opportunity` | A  **built for round 2** as `nfl_xfp_weight` (its own share, alongside ours); nflverse's expected stats are scored with the league's rules. Caveat: nflverse fits its expected-value models on many seasons, possibly including later ones, so this idea may look slightly better in a backtest than it can be live |
| E-05 | `usage-trend` | Target share and carry share trend (last 2 games vs season) replaces the snap-share role factor | player stats | A |
| E-06 | `def-pass-position` | Opponent factor for QB, WR, TE and receiving RB from passing and receiving yards and touchdowns allowed to that position | player stats by opponent | B |
| E-07 | `def-run-position` | Opponent factor for RB and QB runs from rushing yards and touchdowns allowed | player stats by opponent | B |
| E-08 | `def-sack-int` | QB factor from the opponent's sack and interception rates | team stats | B |
| E-09 | `def-schedule-adjust` | Adjust each defense's numbers for the offenses it has faced | player stats | B |
| E-10 | `opp-shrink` | Replace the hard ±25% opponent clamp with shrinkage by games played | none | B |
| E-11 | `team-offense` | Team points and plays per game (trailing) scales every player on the team | team stats | C |
| E-12 | `implied-total` | Team's implied score from the betting spread and total | schedules | C |
| E-13 | `game-script` | Favourites run more and underdogs pass more, from the spread | schedules | C |
| E-14 | `depth-rank` | Depth-chart rank adjustment for RB, WR, TE | `load_depth_charts` | D  **built for round 2** as `depth_rank`: tiers 1 starter / 2 next in line / 3 deeper (2025+ snapshots: the last one taken before the day of the week's first kickoff; WR1-3 starters, WR4-5 next); the effect is the change against his usual tier, sized from earlier seasons' points per tier |
| E-15 | `teammate-out` | Raise a player when a higher-ranked teammate at his position is Out | injuries, depth charts | D  **built for round 2** as `teammate_out`, without depth data: a teammate at his position who outscores him, played in the last 2 weeks, and is Out, Doubtful or on a reserve list this week |
| E-16 | `rookie-prior` | Starting value for players with no history from draft round and pick | `load_draft_picks` | D |
| E-17 | `opener-weights` | Last-season blend weight tuned for weeks 1-4 | none | D |
| E-18 | `role-window` | Role factor window and clamp tuned per position | none | D |
| E-19 | `injury-discount-fit` | Replace the guessed Questionable and Doubtful multipliers with ones fit on past seasons | injury reports | E  **deferred: a backtest only contains players who played, so the discount for players who did not play cannot be measured fairly; needs a different test (projected-and-played versus projected-and-sat)** |
| E-20 | `return-from-injury` | Reduced workload in the first games back from a reserve-list stay | rosters, injuries | E  **built for round 2** as `return_discount`: the first game after reserve-list weeks |
| E-21 | `home-away` | Home or away | schedules | F |
| E-22 | `roof-weather` | Dome, wind and temperature | schedules | F |
| E-23 | `rest-days` | Short weeks and extra rest | schedules | F |
| E-24 | `kicker-model` | Kickers from the team's implied total and dome | schedules | G |
| E-25 | `defense-model` | Defenses from the opponent's implied total and sack and turnover rates | schedules, team stats | G |
| E-26 | `halflife-by-position` | Recency half-life tuned per position | none | H |
| E-27 | `prior-games-by-position` | Last-season weight tuned per position | none | H |
| E-28 | `learned-weights` | A ridge regression combines the features instead of hand-set multipliers | all of the above | H  **second batch: built after the hand-set ideas, from the winners' features** |
| E-29 | `tree-model` | A gradient-boosted model on the same features, compared for accuracy and explainability | all of the above | H  **second batch** |
| E-30 | `blend-best` | A blend of the best hand-set and the best learned model | winners | H  **second batch** |
| E-31 | `ranges-by-format` | Ranges fitted per scoring format | backtest | I  **second batch: ranges are refit after the point projection settles** |
| E-32 | `player-type-ranges` | Wider ranges for boom-or-bust players | backtest | I  **second batch** |
| E-33 | `correlated-sim` | A quarterback and his receivers move together in the simulation | backtest | I  **second batch** |
| E-34 | `receiving_half_life` | RBs: rushing and receiving points averaged apart, receiving with its own memory length (round 2) | player stats | A |
| E-35 | `ypc_regression` | RBs: pull yards per carry partway back toward the league's typical rate, fit on earlier seasons (round 2) | player stats | A |
| E-36 | `carry_volume` | RBs: recent share of team carries against the season share, times the team's expected carries from the spread (fit on earlier seasons), applied to the rushing part (round 2) | player stats, schedules | C |
| E-37 | goal-line carries | RBs: share of team carries inside the 5 | play-by-play | A  **deferred by the owner (2026-11-13): backlog M-24** |

Not planned: quarterback-change effects (covered by E-11 and E-12), routes run and pressure rates (no free per-game source found).

Related: [P4 Build Plan](P4-Build-Plan.md) · [Backtest Report](Backtest-Report.md) · [Improvement Backlog](Improvement-Backlog.md)
