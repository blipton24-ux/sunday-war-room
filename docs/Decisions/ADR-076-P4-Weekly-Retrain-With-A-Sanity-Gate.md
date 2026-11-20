---
title: "ADR-076: Weekly retrain, promoted only through a sanity gate"
date: 2026-11-20
tags: [adr, model, machine-learning, operations, p4]
status: accepted
---
# ADR-076: Weekly retrain, promoted only through a sanity gate

## Context
From P4 step 10 the worker retrains the ML model every Tuesday after the stats ingest, on every game played so far ([ADR-073](ADR-073-P4-Model-Trainings-In-The-Database.md) stores each training). A training can go wrong without failing loudly: a partial nflverse download, a missing column, a bug. Grading a new training on last weekend's games is not a fair check, because it trained on them. Testing retrained every four weeks ([ADR-065](ADR-065-P4-Retrain-Every-Four-Weeks-In-Testing.md)) only to keep 16 test runs affordable.

## Options considered
**The same example:** Tuesday 24 November; the live model projects Puka Nacua 14.0 for week 12.

| | A: weekly, no gate | **B: weekly, sanity gate** | C: gate, every four weeks |
|---|---|---|---|
| A bad download halves every receiver | goes live | blocked; the previous training stays live; the owner is emailed | blocked |
| A normal week (14.0 to 14.3) | live | live | live every fourth week |

## Decision
**Option B** (owner, 2026-11-20). A Tuesday training becomes the live model only if all of these hold; otherwise the previous training stays live, the failure is logged on the training's row and the owner is emailed:
1. every position's models trained (27 targets) and the fitted rates are present;
2. its score on its own held-back season is no more than about 2% worse than the live training's score on its held-back season;
3. for the coming week, no position's average projection moves more than about 10% from the live training's.

The thresholds are settings, checked against the first weeks of live use. The owner's address is a setting, never committed.

## Why
Weekly retraining uses the newest games; the gate catches the realistic failures without grading a model on games it learned from. Check 2 compares each training on data it did not train on; check 3 notices sudden shifts that no fair score would see in time.

## Trade-offs accepted
Weekly retraining is more frequent than what was tested; more recent data is expected to help, and check 2 guards against the opposite. A real change in the game (a team switching to a run-heavy offense) could trip check 3 and need the owner to promote the training by hand.

Related: [ADR-073](ADR-073-P4-Model-Trainings-In-The-Database.md) · [ADR-065](ADR-065-P4-Retrain-Every-Four-Weeks-In-Testing.md) · [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md)
