---
title: "ADR-062: The machine-learning model trains on seasons from 2016"
date: 2026-11-14
tags: [adr, model, machine-learning, data, p4]
status: accepted
---
# ADR-062: Training history starts in 2016

## Context
The XGBoost model ([ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md)) learns from past player-weeks, so more seasons give it more examples. Today the database holds nflverse data from 2021. Older seasons add rows, but the game has changed (more passing, running backs used differently), and older depth charts and injury reports are patchier.

## Options considered

**The same scenario through each option:** training the WR targets model used to test 2022 ([ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) trains only on earlier seasons).

| | From 2021 (today) | **From 2016** | From 2012 (snap counts begin) |
|---|---|---|---|
| Seasons to train the 2022 test on | 1 | **6** | 10 |
| Player-weeks loaded (approx.) | ~100k | **~180k** | ~250k |
| How close to today's game | closest | **close** | includes the more run-heavy early 2010s |
| Gaps in depth charts and injury reports | few | **few** | more |
| Load time and storage | none extra | **moderate** | about 40% more than 2016 |

## Decision
**Load and train on every season from 2016.** Earlier seasons can be added later if the backtest shows the model is short of data.

## Why
With only 2021 onward, the 2022 test season would be judged by a model trained on a single season, too little for a tree model. 2016 gives every test season several seasons of training while staying close to how the game is played now.

## Trade-offs accepted
More data to load and store (still small for PostgreSQL, [ADR-030](ADR-030-Stats-In-PostgreSQL.md)); seasons 2016-2020 need the same schema checks as the newer ones.

Related: [ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md) · [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md)
