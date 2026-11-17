---
title: "ADR-065: The four-season test retrains the model every 4 weeks"
date: 2026-11-17
tags: [adr, model, machine-learning, backtest, p4]
status: accepted
---
# ADR-065: The four-season test retrains the model every 4 weeks

## Context
[ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) tests each season (2022-2025) on a model trained only on earlier seasons, "with the current season's earlier weeks added as it goes", as the app runs live. The feature table already carries a player's earlier games of the season (his averages so far). The open question was whether the trees themselves are retrained during a test season, and how often: one training takes about 1.5 minutes, and live (P4 step 10) retrains every Tuesday.

## Options considered

**The same example through each option:** projecting Puka Nacua for 2024 week 11.

| | A: once per season | **B: every 4 weeks** | C: every week |
|---|---|---|---|
| Trees trained on | 2016-2023 | 2016-2023 plus 2024 weeks 1-8 | 2016-2023 plus 2024 weeks 1-10 |
| Matches live weekly retraining | loosely (a little pessimistic) | closely | exactly |
| Trainings per full check | 4 | about 16 | about 70 |
| Time per full check | about 6 min | about 25 min | about 1¾ hours |

## Decision
**Option B** (owner, 2026-11-17). Each test season is projected in blocks: models are retrained before weeks 1, 5, 9 and 13, and each retrain adds that season's games played so far (`ml/walk_forward.py`, `RETRAIN_WEEKS`). Settings are still chosen on the last full training season; only the final retrain adds the new weeks (`train.fit(..., upto=(season, week))`). Training starts in 2016 for every test season, and every earlier test season becomes training data for the later ones (the 2025 test trains on 2016-2024); the live model trains on 2016 through the latest week.

## Why
Close to how the live model will behave, at a cost that allows repeated checks (settings grid, weak targets) during the build.

## Trade-offs accepted
The first full run took 52 minutes, not 25: training grows with each season, and the 2025 blocks (2016-2024 plus the weeks so far) took about 6 minutes each. Weeks 2-4, 6-8 and so on are projected by trees up to three weeks staler than live would have, so the test slightly understates the live model. Option C stays available for the final check if the result is close.

Related: [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [ADR-062](ADR-062-P4-Training-History-From-2016.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md)
