---
title: "ADR-067: P4 scope: everything that can improve the projection model now"
date: 2026-11-17
tags: [adr, model, machine-learning, scope, p4]
status: accepted
---
# ADR-067: P4 scope: everything that can improve the projection model now

## Context
After the four-season verdict (the ML model passes [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md)'s ship rule in every format, [ML Evaluation Report](../Build-Plan/ML-Evaluation-Report.md)), the owner asked for every projection-model item that can be fixed or tested now to be done inside P4, so P4 ends with the best model we can build for now. The [Improvement Backlog](../Build-Plan/Improvement-Backlog.md) was cleaned up the same day (2026-11-17): seven items signed off, three closed, seven added (M-28 to M-34).

## Decision (owner, 2026-11-17)
1. **Accuracy experiments, in P4 step 7**, each kept only if it beats noise in the four-season test (ADR-061, decision 5):
   - fitted availability: how often Questionable, Doubtful and backup players really play (M-29), together with how Questionable players are shown (projected as if playing, dropped to 0 when ruled out, trimmed by news) and injury news (M-34); both need their own side-by-side first;
   - red-zone and goal-line usage from play-by-play (M-24; a data-source ADR first), which can also score M-12 and M-17;
   - a tuning run: wider settings grid (M-26), the plain average for weak targets (M-27), training from 2012 (M-31, amends [ADR-062](ADR-062-P4-Training-History-From-2016.md) if kept);
   - new signals (M-33) and the blend with 1.0.0 (M-30).
2. **Rest of season (M-15) comes into P4 as a separate long-range model**, a new step; it amends [ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md), which had left it out. It ships when it beats the current rest-of-season method on its backtest.
3. **Late injuries (M-10)** are decided in step 10, with the live compute.
4. **The Accuracy page's version switch (U-17)** and **unmatched players (M-13, M-19)** are done before 2.0.0 ships (step 11).
5. **Injury-game marking**, second-half injuries: a game is also marked "hurt during the game" when his snaps fell below 80% of his normal and the next game shows Out, Doubtful or a reserve listing (below half, any designation counts, as before). A hand check of 16 known in-game injuries found the old rule missed second-half injuries (Kupp 2024 week 2, Jefferson 2023 week 5, Tua 2024 week 2); requiring the strong evidence in the new band keeps knocks tagged Questionable out. The rule changed from a hand check, never from model results (ADR-061, decision 6). Marked games 2022-2025: 278 to 459; the ML verdict is unchanged (half PPR -0.239 to -0.227).

## Why
The verdict showed the model is worth shipping; these items are the ones with evidence or a clear reason to expect a gain, and doing them now means 2.0.0 ships as the best version we can build with the data available.

## Trade-offs accepted
P4 grows by roughly two to three working sessions, and several items need long training runs (about an hour each). Out of P4 still: IDP (M-18) and correlated simulation (M-07, win probability rather than projections).

Related: [ADR-060](ADR-060-P4-Machine-Learning-Stats-Then-Score.md) · [ADR-061](ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md) · [ADR-062](ADR-062-P4-Training-History-From-2016.md) · [Improvement Backlog](../Build-Plan/Improvement-Backlog.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md)
