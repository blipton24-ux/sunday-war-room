---
title: "Machine learning and XGBoost"
date: 2026-11-14
tags: [concept, model, machine-learning]
---
# Machine learning and XGBoost

**Machine learning** = the computer learns the rules from past examples instead of a person writing them. You show it thousands of past player-weeks ("these were his signals; he got 9 targets"), and it finds the pattern that best predicts what happened.

## Three ways to turn signals into a projection
1. **Hand-written rules** (model 1.0.0): a person decides the recipe, e.g. recent average × opponent factor × role factor, and picks every number.
2. **Linear model** (ridge regression): the computer learns one weight per signal and adds them up. It is simple and exact to explain, but it only learns straight-line effects.
3. **Gradient-boosted trees** (XGBoost, Sunday War Room's choice in [ADR-060](../Decisions/ADR-060-P4-Machine-Learning-Stats-Then-Score.md)): the computer learns many small yes/no flowcharts, each one fixing the mistakes of the ones before, and adds up their answers.

## How a boosted tree model learns
```
Tree 1:  everyone starts at the average (5.5 targets)
         target share > 20%?  yes → +2.0    no → −1.5
Tree 2:  looks at what tree 1 still got wrong
         team implied score > 24?  yes → +0.6   no → −0.3
Tree 3:  ...opponent bottom-10 against receivers? → +0.4
  ...  hundreds of small trees
Prediction = 5.5 + 2.0 + 0.6 + 0.4 + … = 8.1 targets
```
Each tree is small (a few questions deep), so no single tree can memorise the data. **Boosting** means each new tree is trained on the leftover errors of the trees so far.

## Side by side: a wide receiver's Week 11 targets
| | Hand-written | Linear (ridge) | XGBoost |
|---|---|---|---|
| Who decides the recipe | a person | the computer, straight lines only | the computer, any shape |
| "A high team score helps only if he's the main target" | only if someone writes it | only if someone adds that combination | found on its own |
| Same signal counted twice (strong offense in his points and in a team factor) | yes | no | no |
| Explaining "why 8.1" | exact | exact | exact for the model: XGBoost reports how much each signal added (`pred_contribs`) |
| Main risk | missing effects | missing curved effects | **overfitting**: learning the noise of past games |

## Overfitting, and how we guard against it
A flexible model can "memorise" last season, including its luck, and then do worse on new games. Three guards ([ADR-061](../Decisions/ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md)):
- **Walk-forward testing:** to test 2024, train only on seasons before 2024, like the live app, which only knows the past.
- **Settings chosen on training seasons only:** tree depth, learning rate and the number of trees are picked with part of the training data held back; **early stopping** stops adding trees once that held-back part stops improving.
- **A final look at unseen weeks** (the 2026 season so far) before a version ships.

## Words you'll see
- **Feature:** one input signal (target share, implied team score). The **feature table** is one row per player-week.
- **Target:** what a model predicts (targets, catch rate, …). Confusingly, also a football stat here.
- **Training / test data:** games the model learns from / games it is graded on.
- **Hyperparameters:** the model's settings (tree depth, learning rate), chosen before training.
- **Poisson objective:** a training mode for counts (targets, touchdowns) that can't go below zero.
- **Leakage:** a feature that secretly knows the future (the final injury report, the recorded wind). It makes a backtest look better than the live app will be.

Related: [ADR-060](../Decisions/ADR-060-P4-Machine-Learning-Stats-Then-Score.md) · [ADR-061](../Decisions/ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md) · [Projection Model](../Specs/Projection-Model.md) · [Backend Basics](Backend-Basics.md)
