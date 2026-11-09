---
title: "ADR-002: Fresh build, learn from old projects"
date: 2026-11-08
tags: [adr, process]
status: accepted
---
# ADR-002: Fresh build; learn from the old projects

## Context
Two earlier projects exist: `fantasy-football-assistant` (ESPN sync, nflverse projection model, accuracy grading) and its fork `fantasy-football-app` (Sunday War Room: accounts, multi-league). Sunday War Room could build on them or start over.

## Options considered
| Option | Upside | Downside |
|---|---|---|
| **Fresh build, learn from old** | All code written and understood fresh; lessons are not lost | Slower than forking |
| Fork an existing project | Fastest | Inherits old decisions (SQLite, desktop window, single user) |
| Completely clean slate | Purest learning | Repeats mistakes the old projects already solved |

## Decision
New code written from scratch. The old projects are reviewed for lessons ([Lessons from Old Projects](../Lessons-from-Old-Projects.md)), and **each specific reuse needs the owner's approval**.

## Why
Every line should be understood and intentional. A fresh build on a modern, deployed stack also closes the gaps the old projects leave: never deployed, no CI, no containers, single user.

Related: [Lessons from Old Projects](../Lessons-from-Old-Projects.md) · [ADR-008 Own projection model](ADR-008-Own-Projection-Model.md)
