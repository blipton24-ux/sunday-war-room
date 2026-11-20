---
title: "ADR-060: P4 restarts as a machine-learning model: predict the stats with XGBoost, then score them"
date: 2026-11-14
tags: [adr, model, machine-learning, p4]
status: accepted
---
# ADR-060: P4 restarts as a machine-learning model that predicts stats, then scores them

Replaces the first P4 approach (ADR-054 to ADR-059, removed from the vault 2026-11-14; they remain in git history). How the new model is tested and shipped is [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md).

## Context
Model 1.0.0 projects **points**: a recent-weighted average of a player's fantasy points, times an opponent factor and a snap-share factor. The first P4 approach added more multipliers (betting market, touchdown luck, carry volume and about thirty others), each with a dial, and tuned the dials position by position. After two rounds it had shipped one position (running backs, model 1.1.0, about 0.17 points better per startable back on 2025) and showed three limits that more dials cannot fix:

1. **It only sees points.** A 2-catch, 80-yard, one-touchdown game and a 10-catch, 80-yard game look almost the same, though the second says far more about next week.
2. **Multipliers double count.** A player on a strong offense already scores well, so multiplying by "strong offense" counts it twice. Team-offense, implied-total and schedule-adjusted defense all made projections worse as blanket multipliers in round 1.
3. **Dials are tuned one at a time.** Ideas that only help together (carry volume plus a tighter role limit, for running backs) are found by luck, and every new idea is another dial.

The earlier project's model reached 5.83 points of average miss on startable players (2025, full PPR) against 6.45 for model 1.0.0, so there is room to improve.

## Options considered

**The same scenario through each option:** a wide receiver, Week 11, full PPR.

| Option | How Week 11 is projected | Example |
|---|---|---|
| A. Points with hand-set multipliers (the first P4 approach) | Recent points average, times a dial-tuned factor for each idea | 15.2 × 1.05 opponent × 1.00 role = 16.0 |
| B. Stats, then score, with hand-set formulas | We write the recipe for each stat; a tuner sets the amounts | targets = (70% recent share + 30% season share) × team's expected pass attempts, then catch rate, yards and touchdowns the same way, then scored |
| C. Stats, then score, with ridge regression | The computer learns one weight per signal from past seasons and adds them up | targets = 0.52 × recent share × team attempts + 0.31 × season share × team attempts + 0.9 × opponent effect − … |
| **D. Stats, then score, with XGBoost (gradient-boosted trees)** | The computer learns hundreds of small yes/no trees, each correcting the ones before; their answers add up | "recent target share above 22%? → team implied score above 24? → opponent bottom-10 against receivers? → +1.3 targets", summed over every tree → 8.1 targets, 66% caught, 12.4 yards a catch, 0.45 touchdowns → 5.4 catches, 66 yards → **16.3 in full PPR, 13.6 in half PPR** |

| | A. Multipliers | B. Hand-set stats | C. Ridge | D. XGBoost |
|---|---|---|---|---|
| Sees how points were made | no | yes | yes | yes |
| Double counting | yes | possible | handled | handled |
| "Only when this is also true" effects | only if written as a dial | only if written | only if built in by hand | **found by the model** |
| Adding a new signal | a new dial to tune | a new formula | a new column | **a new column** |
| Any league's scoring exact | no (one fit reused) | yes | yes | yes |
| Explanation on the Player screen | exact | exact | exact | per-signal contributions computed by XGBoost (exact for the model, grouped into plain categories) |
| Overfitting risk | grows with dials | low | low | higher; controlled by tuning on earlier seasons only ([ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md)) |
| Build effort (estimate) | done | ~3½ sessions | ~4 sessions | ~4½–5½ sessions |
| Upkeep | re-tune dials | re-tune formulas | weekly retrain, automatic | weekly retrain, automatic; re-tune model settings once a season; pin the XGBoost version |

## Decision
**D. Predict each stat with XGBoost, then score the predicted stats with each league's own rules.** One model only: no ridge model is built alongside it.

1. **Stats, then score.** For each position, XGBoost predicts the player's **volume** (targets, carries, pass attempts) and his **efficiency** per opportunity (catch rate, yards per catch, yards per carry, touchdowns per opportunity, completion rate, yards per attempt, interceptions per attempt). Volume × efficiency gives expected stats, and the league's own scoring turns them into points.
2. **Learned from past seasons only.** Training for a season uses only earlier games; the model is retrained weekly on everything played before the week being projected.
3. **Explainable.** XGBoost reports how much each signal moved each prediction. These are grouped into plain categories (his role, team volume, opponent, betting market, injury and depth, history) and converted to fantasy points for the Player screen's "why this number" factors.
4. **The first P4 approach is removed.** Its idea switches (`ModelConfig` and the idea branches in `projection.py`), the tuners (`tune.py`), the experiment ledger, the tuning pages and model 1.1.0 (running backs) are deleted; the live model returns to the 1.0.0 method until the new model ships. **The measuring tools stay**: the walk-forward backtest, the paired comparison with its bootstrap noise check, the startable-player slice, injury-game marking, the stored betting lines, injury reports, reserve lists and status snapshots, and version-safe screens. Feature code from the first approach that computes a signal (target and carry share, defense allowed by position, betting-line context) may be reused as columns in the new feature table.
5. **Earlier-project techniques stay ideas only** (carried over from the removed ADR-056, amending [ADR-031](ADR-031-Approved-Reuses.md)): every technique listed in the vault may be used as an idea, written fresh here and refit on our own data; nothing is copied. A technique from the older projects not already listed needs its own approval ([ADR-002](ADR-002-Fresh-Build.md)).
6. **Scope: weekly accuracy** (carried over from the removed ADR-057). Smarter rest-of-season value (M-15), IDP (M-18) and keeper/dynasty value stay out of P4. Rest-of-season numbers follow the weekly model, so the backtest keeps checking they do not get worse.

## Why
The model is what every recommendation in the app rests on (start/sit, waivers, trades, win chance), so it gets the most accurate approach that can still explain itself. Gradient-boosted trees are the standard choice for this kind of data (one row per player-week, a few dozen numeric signals) and learn interactions and double counting that the multiplier approach had to hand-tune. Predicting stats instead of points uses what the free data actually holds (targets, carries, yards, touchdowns) and makes every scoring format exact.

## Trade-offs accepted
- About one more session to build than ridge regression, mostly tuning the model's settings and building the explanations.
- Higher overfitting risk than a linear model; handled by tuning only on earlier seasons and judging on later ones ([ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md)).
- Explanations are the model's own per-signal contributions rather than a fixed formula a person could recompute by hand.
- The measured running-back gain from 1.1.0 is given up until the new model ships; the new model must beat 1.0.0 and should beat 1.1.0's numbers to justify the restart.
- A new dependency (`xgboost`, CPU build, pinned with uv per [ADR-039](ADR-039-Python-Dependency-Lock-uv.md)); upgrading it can shift numbers, so an upgrade is re-tested like a model change.

Related: [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [ADR-008](ADR-008-Own-Projection-Model.md) · [ADR-034](ADR-034-Ship-Model-v1-Upgrade-Later.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Projection Model](../Specs/Projection-Model.md) · [Machine learning and XGBoost](../Concepts/Machine-Learning-and-XGBoost.md)
