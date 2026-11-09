---
title: "ADR-033: The app is named Sunday War Room"
date: 2026-11-08
tags: [adr, product, brand]
status: accepted
supersedes: ADR-028 (repo name only)
---
# ADR-033: The app is named Sunday War Room

## Context
The working name was **FFCC (Fantasy Football Command Center)**. With the Sunday War Room visual style chosen ([ADR-032](ADR-032-Visual-Sunday-War-Room-Style.md)), the owner chose to carry over that name and logo too.

## Options considered
| Option | Meaning |
|---|---|
| **Rename to Sunday War Room** | App, docs and repo all use the Sunday War Room name and logo |
| Keep FFCC, borrow the look | App stays FFCC; only the visual style is reused |

## Decision
- Product name: **Sunday War Room**. Logo: the war-room table mark, in its **flat** version (no gradients).
- GitHub repo name: **`sunday-war-room`**. This replaces `fantasy-football-command-center` from [ADR-028](ADR-028-Repo-Name-and-License.md); the license decision there still stands.
- The local project folder stays `FFCC/` for now. Renaming it is cosmetic and can happen at any time.
- Older notes may still say "FFCC"; it means this project.

## Trade-offs accepted
The owner's earlier prototype (`fantasy-football-app/`) also uses this name. It remains a separate, local-only prototype; this project is the production app.

Related: [ADR-032 Visual style](ADR-032-Visual-Sunday-War-Room-Style.md) · [ADR-028 Repo and license](ADR-028-Repo-Name-and-License.md)
