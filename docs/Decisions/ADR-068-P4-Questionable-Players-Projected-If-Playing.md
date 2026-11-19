---
title: "ADR-068: Questionable players are projected as if they play, with the chance shown beside it"
date: 2026-11-18
tags: [adr, model, injuries, p4]
status: accepted
---
# ADR-068: Questionable players are projected as if they play, with the chance shown beside it

## Context
1.0.0 multiplies a Questionable player by 0.92 and a Doubtful one by 0.25, both set by hand. That one number is doing two jobs: the chance he sits, and how much less he scores when he plays hurt. P4 step 7 measured both on 2016-2025 (backlog M-29), counting "played" as any offensive snap (snap counts, so a blocking tight end with no stats still counts):

| Final report | Played |
|---|---|
| Out | 0.1% |
| Doubtful | 1% |
| Questionable, usual starter (median snap share 60%+) | 77% (QB 52%, RB 75%, WR 77%, TE 80%) |
| Questionable, others | 54% |
| Questionable by Friday practice | full 75%, limited 64%, none 41% |

When a Questionable player does play, he scores below his "if he plays" projection (2022-2025 startable, half PPR, against healthy players' average miss): about 1.2 points lower for WR, 0.9 for RB and 1.2 for QB. The ML model only partly learns this from its injury-report input. Teams name inactives 90 minutes before kickoff, so the chance he sits only matters until then.

## Options considered

**The same example through each option:** Puka Nacua is Questionable (hamstring, limited Friday); the model says 15.0 half PPR if he plays.

| | **A: if he plays, trimmed** | B: chance-weighted | C: keep 1.0.0 |
|---|---|---|---|
| Number shown before inactives | about 14 (15.0 less the measured trim), with "Q · plays ~70%" | about 10 (14 x 70%) | 13.8 (15.0 x 0.92) |
| Ruled Out or inactive | 0 | 0 | 0 |
| Win probability, team totals | use the chance-weighted value behind the scenes | same number | same number |
| Weak spot | the number alone ignores the risk; the badge carries it | he never scores 10: about 14 or 0; looks wrong, can bench a player who plays | hand-set; Doubtful badly off (25% vs 1%) |

## Decision
**Option A** (owner, 2026-11-18).
- The models give two fitted numbers per position, refit at every training like the rest of the model:
  - **chance he plays** by report status (Questionable, Doubtful) and whether he is a starter on the depth chart, counted from snap counts;
  - **trim when he plays**, Questionable and Doubtful, fitted out of sample on the held-back season and pulled toward no trim when there are few games.
- A projection is the trimmed "if he plays" number; Out, IR, PUP and Suspended stay 0; the backup quarterback discount stays. Each projection also carries the chance he plays and the chance-weighted value, which win probability and team totals use.
- **Grading** (owner, 2026-11-18): the evaluation grades the shown "if he plays" number against games he played; a Questionable or Doubtful player who sat is left out of the grade (the walk-forward only grades player-games with stats, so this is how it already works). Whether he plays is graded separately, through the chance he plays.
- Injury news ("expected to be limited") and a later status change near kickoff come with the live work in step 10 (M-10, M-34).

## Why
It matches how fantasy players read a projection ("what does he score if he suits up?") and how other apps show it, while keeping the risk visible and keeping win probability honest. Splitting the hand-set 0.92 into two measured numbers makes each one testable.

## Result
Four test seasons 2022-2025, startable players, injury games left out, average miss in points ([ML Evaluation Report](../Build-Plan/ML-Evaluation-Report.md), 2026-11-19), against the same model with the 1.0.0 rules: half PPR 5.489 to 5.472, full 5.967 to 5.946, standard 5.049 to 5.035; lower in every season and at every position, most for receivers, least for quarterbacks (few Questionable quarterback games, so their trim stays near none). The ship rule still passes in all three formats. Against Sleeper's projections on the same games: 5.476 against 5.477 (half PPR).

## Trade-offs accepted
A start/sit list sorted by the shown number treats a Questionable player as if he plays; whether lineup advice uses the shown or the chance-weighted value is decided with the live wiring in step 10. Practice status changes the chance a lot (41% to 75%) but is not in the live player feed yet, so it is left out for now (backlog M-35).

Related: [ADR-067](ADR-067-P4-Scope-For-The-Best-Model-Now.md) · [ADR-064](ADR-064-P4-Spread-Aware-Scoring-Of-Predicted-Stats.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md)
