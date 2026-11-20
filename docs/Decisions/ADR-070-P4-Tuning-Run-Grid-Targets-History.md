---
title: "ADR-070: Tuning run: a wider settings grid, the model for every target, 2012 history tested"
date: 2026-11-20
tags: [adr, model, machine-learning, tuning, p4]
status: accepted
---
# ADR-070: Tuning run: a wider settings grid, the model for every target, 2012 history tested

## Context
P4 step 7's tuning run (decision D1 in the [P4 Build Plan](../Build-Plan/P4-Build-Plan.md)) covers three backlog items:
- **M-26:** training tries 12 settings (depth 3 or 5, leaf size 10, 50 or 200, column share 0.5 or 0.8) and most models picked an edge (depth 5 or leaf size 200), so better values may lie beyond it.
- **M-27:** against the player's own season-to-date value, touchdown rates only tie (RB rush TD -0.6%, WR rec TD -1.5%, TE rec TD +0.5%), QB rush TD rate is worse in all four seasons (+3.4%) and WR carries slightly worse (+5%) ([ML Training Report](../Build-Plan/ML-Training-Report.md)).
- **M-31:** training starts in 2016 ([ADR-062](ADR-062-P4-Training-History-From-2016.md)); 2012 is the first season with every input (snap counts begin).

## Options considered
**The same example:** Puka Nacua's touchdown rate, 5 touchdowns on 80 targets so far (6.3% a target).

| Part | Options | Chosen |
|---|---|---|
| Settings grid | A keep 12; **B 24: depth 3, 5, 7 and leaf size 10, 50, 200, 500** (about twice the training time); C shift to depth 5, 7 and leaf 50-500 | **B** |
| Weak targets | **A the model for every target**; B per training, whichever of model and season-to-date value wins on the held-back season; C the season-to-date value for the five weak targets for good | **A** |
| History | A keep 2016; B switch to 2012; **C load 2012-2015 and keep it only if it beats 2016 beyond chance** | **C** |

## Decision
Owner, 2026-11-20:
- **Grid B.** Settings are still picked inside the training seasons only ([ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md)); the four-season evaluation takes about twice as long.
- **Weak targets A.** Every target keeps its model; Puka's touchdown rate comes from the model. Touchdowns are left to the play-by-play usage signal (M-24, decision D2).
- **History C.** 2012-2015 are loaded and the model trained from 2012 is compared with the one trained from 2016 on the same test games (paired bootstrap); 2012 replaces 2016 only if it is better beyond chance, and ADR-062 is then superseded.

## Why
The wider grid costs only unattended computer time. Keeping one method for every target keeps the pipeline simple, and the weak targets are tied rather than clearly worse except QB rushing touchdowns, which are a small share of points. A longer history may help rare events or may teach an older style of play, so it is measured, not assumed.

## Trade-offs accepted
QB rushing touchdown rate stays slightly worse than the season-to-date value until play-by-play (or another signal) improves it; the backlog keeps M-27 open for that. Each evaluation run grows to about 100 minutes.

Related: [ADR-062](ADR-062-P4-Training-History-From-2016.md) · [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [ADR-067](ADR-067-P4-Scope-For-The-Best-Model-Now.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md)
