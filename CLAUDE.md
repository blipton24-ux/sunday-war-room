# CLAUDE.md

Guidance for Claude Code when working in `FFCC/`.

## What this is

**Sunday War Room** (the folder keeps its old working name, FFCC): a public,
multi-tenant fantasy football web app (PWA). Visual reference:
`mockups/p1-screens-v3.html` (ADR-032). Built fresh; earlier fantasy-football projects are
prior art only, and nothing is copied from them without the owner approving
that specific reuse (ADR-002).

## The vault is the source of truth

`docs/` is an Obsidian vault holding every decision, spec and concept note.
Read `docs/README.md` first, then the relevant ADRs in `docs/Decisions/`
and specs in `docs/Specs/` before changing anything. **The owner makes every
decision.** If work needs a choice the vault does not already settle, follow
ADR-003: explain the options in plain language, show a concrete side-by-side
example, recommend one, ask, and record the answer as a new ADR.

## Public vs private (ADR-027)

This repo is public. Public notes give **engineering reasons only**. Anything
personal (goals, study notes, practice material) goes in
`docs/Private/`, which is git-ignored. Public notes never link into
`docs/Private/`. Personal working preferences live in `CLAUDE.local.md`
(git-ignored).

## Vault conventions

Relative markdown links (no wikilinks), no spaces in file names, frontmatter
(`title`, `date`, `tags`), every note ends with a `Related:` line. Lint with
the `obsidian-notes` skill after editing.

## Status

Vault written and pre-build decisions made (ADR-028 to ADR-033), 2026-11-08. Next: Phase 1 build per
`docs/Build-Plan/P1-Build-Plan.md`. P1 build in progress: steps 1–3 done (compose db+redis,
API skeleton, schema + first migration); see `api/README.md`.
