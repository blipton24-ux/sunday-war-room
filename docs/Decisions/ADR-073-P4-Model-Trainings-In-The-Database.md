---
title: "ADR-073: Trained models live in the database; the version names the method"
date: 2026-11-20
tags: [adr, model, machine-learning, storage, p4]
status: accepted
---
# ADR-073: Trained models live in the database; the version names the method

## Context
From P4 step 10 the worker retrains the ML model every Tuesday and the API projects with it. A training is a set of files (one XGBoost model per position and target, plus the fitted minor-stat rates, spreads, trims and chances to play; `ml/train.py` `save`/`load`), estimated at tens of MB. The worker and the API run in separate containers. Projections carry `model_version` and are frozen at kickoff; the Accuracy page groups grades by version.

## Options considered
**The same example:** Puka Nacua's week 12 projection, made with the training of Tuesday 24 November (games through week 11).

Where the files live:

| | **A: database** | B: shared disk | C: cloud file storage |
|---|---|---|---|
| How | a `model_trainings` row per training: when, data through which week, its held-back score, and the files | a folder both containers mount | an outside storage service |
| On a small container host (P8) | works: the database is already there | often not: disks are not shared or not kept | works, one more service and bill |
| Backups and history | with everything else; every training kept | separate | separate |

What the version means:

| | **V1: the method** | V2: every retrain |
|---|---|---|
| Puka's row | "2.0.0", training of 24 November | "2.0.7" |
| Accuracy page | one line for 2.0.0 all season | a new version each week |

## Decision
**A and V1** (owner, 2026-11-20).
- A `model_trainings` table holds every training: id, method version, trained at, the last season and week of data, the held-back score, and the model files. The live model is the newest training allowed live (the Tuesday safety check, decision D7).
- `model_version` changes only when the method changes (2.0.0, then 2.1.0 with kickers and defenses); each projection row also records the training that made it.
- Trainings are kept, so any past projection can be reproduced.

## Why
The database is the one store both containers already share on any host, it is backed up already, and keeping every training costs little. Versioning the method keeps the Accuracy page readable while each row still says exactly which training produced it.

## Trade-offs accepted
The database grows by tens of MB a week during the season (about 1 GB a season if every training is kept); old trainings can be pruned later, keeping those that produced frozen projections.

Related: [ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md) · [ADR-065](ADR-065-P4-Retrain-Every-Four-Weeks-In-Testing.md) · [ADR-030](ADR-030-Stats-In-PostgreSQL.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md)
