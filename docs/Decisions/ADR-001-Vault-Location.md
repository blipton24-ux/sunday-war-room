---
title: "ADR-001: Vault lives in FFCC/docs"
date: 2026-11-08
tags: [adr, process, documentation]
status: accepted
---
# ADR-001: Vault lives in `FFCC/docs`

## Context
Sunday War Room's decisions, specs and explanations need a home that the owner can browse in Obsidian, that Claude can read while building, and that anyone browsing the repo can read.

## Options considered
| Option | Upside | Downside |
|---|---|---|
| **`FFCC/docs/` inside the project** | Versioned with git next to the code; visible on GitHub | Notes and code share one repo |
| Separate vault elsewhere (e.g. Documents) | Clean separation | Not versioned with code; invisible on GitHub |
| Whole `FFCC/` folder as the vault | Simplest | Obsidian shows code folders, cluttering the graph |

## Decision
The vault is `FFCC/docs/`. It uses relative markdown links so the same notes render in Obsidian, on GitHub and in VS Code.

## Why
A decision log that lives with the code keeps the *why* next to the *what*: future changes can see what was considered and rejected.

## Trade-offs accepted
Docs changes appear in the same git history as code changes.

Related: [ADR-026 Execution order](ADR-026-Execution-Order.md) · [Home](../README.md)
