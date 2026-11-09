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

## Improvement backlog

`docs/Build-Plan/Improvement-Backlog.md` is the running list of things to improve later
(projection model, UI, platform). **Whenever you notice a gap, a weak measurement or a
shortcut, add a row** with its evidence and priority instead of leaving it in chat; when an item
ships, move it to Done. It lists improvements, not decisions: anything that needs a choice still
follows ADR-003.

`docs/Build-Plan/Verification-Gaps.md` lists things that are **built but not yet seen working**
(no browser check, no real credentials). Add a row whenever something ships unwatched; move it
to Verified when it's tested.

## Status

Vault written and pre-build decisions made (ADR-028 to ADR-033), 2026-11-08. Next: Phase 1 build per
`docs/Build-Plan/P1-Build-Plan.md`. P1 build in progress: steps 1–15 done (backend complete: compose db+redis,
schema, auth, Sleeper adapter, worker + jobs, nflverse ingest, projection model v1 + backtest,
matchup/lineup/accuracy endpoints, committed OpenAPI spec + generated TS client in
`web/src/lib/api`, Next.js app with Better Auth sign-in, onboarding and the P1 screens);
PWA manifest, icons, small service worker and install card); see `api/README.md` and `web/README.md`.
Docker images for api (also the worker and the migration) and web, one `docker compose up --build`).
Step 14 tests done: 160 backend tests (99% coverage), 71 web unit tests, 62 Playwright end-to-end tests (`web/e2e/README.md`). Step 15 (CI) done, green on GitHub (2026-11-09): `.github/workflows/ci.yml` + `docs/Build-Plan/CI.md`. Deploy moved to Phase 5 (ADR-042). Next: step 17 (docs), then P2.
Backend change workflow: edit the API, then `python -m app.scripts.export_openapi` and
`npm run generate:api` (in `web/`), and commit `api/openapi.json` and the generated client together.
