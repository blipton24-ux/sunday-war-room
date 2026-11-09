---
title: "ADR-027: Public engineering docs, private personal notes"
date: 2026-11-08
tags: [adr, process, documentation, privacy]
status: accepted
---
# ADR-027: Public engineering docs; personal notes stay private

## Context
The repo will be public on GitHub ([ADR-021](ADR-021-GitHub-CICD.md)), including this vault. Some planning notes are personal (goals, study notes, practice material) and shouldn't be published.

## Options considered
| | **Split public/private** | Whole vault private | Private GitHub repo |
|---|---|---|---|
| Code visible publicly | ✅ | ✅ | ❌ invite only |
| Design decisions visible | ✅ engineering reasons | ❌ | ❌ |
| Personal notes visible | ❌ | ❌ | ❌ |
| Effort | Reword public notes once | Tiny | None |

## Decision
- Public notes (Decisions, Specs, Concepts, Build Plan) give **engineering reasons only**.
- Personal notes live in **`docs/Private/`**, which is **git-ignored**. Public notes never link into it.
- Personal instructions for the AI coding assistant live in **`CLAUDE.local.md`** (also git-ignored). `CLAUDE.md` holds only project rules.

## Trade-offs accepted
`docs/Private/` isn't backed up by git, so it needs a separate backup if wanted.

Related: [ADR-001 Vault location](ADR-001-Vault-Location.md) · [ADR-021 GitHub CI/CD](ADR-021-GitHub-CICD.md)
