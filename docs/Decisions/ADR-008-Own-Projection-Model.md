---
title: "ADR-008: Own projection model from nflverse data"
date: 2026-11-08
tags: [adr, data-science, model]
status: accepted
---
# ADR-008: Build our own projection model from nflverse data

## Context
Every recommendation (start/sit, waivers, trades, the AI agent) depends on projected points.

## Options considered
| Option | Upside | Downside |
|---|---|---|
| **Own model from nflverse** | Full control; transparent, explainable reasoning | More work |
| Platform/external projections | Little work | Numbers can't be explained or improved |
| Both, compared with an accuracy scoreboard | Strongest validation | Most work |

## Decision
Our own model, a **cleaner rebuild** of the old project's lessons, from free nflverse data read in Python ([ADR-013](ADR-013-Backend-FastAPI.md)). An accuracy scoreboard against external projections can be added later.

## Lessons carried forward (each reuse needs approval)
- Projections are **frozen at kickoff** and graded only on rows computed before kickoff.
- Every projection carries its **factors** (recent average, opponent, injury), not just a number.
- Projections are a **range** (distribution), and lineup choices can use win probability.
- A `model_version` on every stored projection; never compare numbers from different versions.
- nflverse file renames must **fail loudly** (schema contracts), never silently fall back to old data.

Full detail: [Projection Model spec](../Specs/Projection-Model.md) · [Lessons from Old Projects](../Lessons-from-Old-Projects.md)

Related: [Projection Model](../Specs/Projection-Model.md) · [ADR-016 Ingestion](ADR-016-Ingestion-Job-Queue.md)
