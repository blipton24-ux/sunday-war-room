---
title: "ADR-075: Start/sit advice for a Questionable player: start him if active, with a named fallback"
date: 2026-11-20
tags: [adr, lineup, injuries, p4]
status: accepted
---
# ADR-075: Start/sit advice for a Questionable player: start him if active, with a named fallback

## Context
[ADR-068](ADR-068-P4-Questionable-Players-Projected-If-Playing.md) gives a Questionable or Doubtful player a shown "if he plays" number and a chance-weighted value; win probability and team totals use the chance-weighted value, and which one start/sit advice uses was left to P4 step 10. A player can be swapped out until his own game locks, and inactives are named 90 minutes before kickoff; late status changes reach projections before the freeze ([ADR-074](ADR-074-P4-Late-Injuries-ESPN-Feed-And-Sunday-Sleeper-Fetch.md)).

## Options considered
**The same example:** Puka Nacua is Questionable, limited Friday: 14.0 if he plays, 64% to play, 9.0 chance-weighted. The bench receiver is healthy at 10.5.

| | A: shown number | B: chance-weighted | **C: start if active, named fallback** |
|---|---|---|---|
| Advice | start Puka | start the bench receiver | start Puka if active (inactives 11:30 Eastern); if he is out, start the bench receiver |
| Puka plays | best | a 14-point player benched | best |
| Puka sits | 0 unless checked | best | the advice switches and an alert goes out before kickoff |

## Decision
**Option C** (owner, 2026-11-20).
- The lineup is built on the shown "if he plays" numbers. For each Questionable or Doubtful starter the advice names the best fallback and when his status is due (90 minutes before his kickoff).
- If that fallback's game locks before the starter's status is due, the choice is made now on the chance-weighted values, and the advice says why ("bench receiver locks at 1 PM, before Puka's status").
- When a status changes before kickoff (ADR-074), the advice and alerts update.

## Why
It follows how a manager handles a Questionable starter: plan, check inactives, swap if needed. The chance-weighted value is the right rule only when the decision must be made before the news, and C uses it exactly then.

## Trade-offs accepted
More logic in the lineup service (a fallback per Questionable starter, lock times compared) and one more line on the screen. A manager who never checks before kickoff relies on the alert.

Related: [ADR-068](ADR-068-P4-Questionable-Players-Projected-If-Playing.md) · [ADR-074](ADR-074-P4-Late-Injuries-ESPN-Feed-And-Sunday-Sleeper-Fetch.md) · [P4 Build Plan](../Build-Plan/P4-Build-Plan.md)
