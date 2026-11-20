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
Step 14 tests done: 160 backend tests (99% coverage), 71 web unit tests, 62 Playwright end-to-end tests (`web/e2e/README.md`). Step 15 (CI) done, green on GitHub (2026-11-09): `.github/workflows/ci.yml` + `docs/Build-Plan/CI.md`. P1 done except deploy. **P2 built (2026-11-10)**: waivers, trade analyzer, live game day (ADR-044..048, `docs/Build-Plan/P2-Build-Plan.md`); 260 backend / 73 web / 81 E2E tests. Phases reordered (ADR-049/050, 2026-11-10): P3 ESPN · P4 improved model · P5 AI assistant + strategy tendencies · P6 UI/UX overhaul · P7 Yahoo · P8 deploy + push alerts. **P3 (ESPN) built and merged to `main` (PR #1, 2026-11-14) except the real-league check** (ADR-050..053, `docs/Build-Plan/P3-Build-Plan.md`): link first with a guided cookie paste for private leagues, a user's own cookies only, Fernet-encrypted credentials (`CREDENTIALS_KEYS`), our own ESPN client and scoring map, a banner and "Reconnect ESPN" state when cookies expire. Everything ESPN-shaped is tested on **synthetic** responses only; **step 15 (the owner's real private league, with his real cookies) is the open item**, and Verification Gaps V-36..V-42 list what it must prove. Never commit real ESPN responses or cookies: scrub first (the repo is public).
**P4 restarted 2026-11-14 as a machine-learning model** (ADR-060, ADR-061, `docs/Build-Plan/P4-Build-Plan.md`): XGBoost predicts each player's stats (volume: targets, carries, pass attempts; efficiency per opportunity), and each league's scoring turns them into points; tested season by season walk-forward on 2022-2025 with settings chosen inside the training seasons, one look at the 2026 weeks before shipping as 2.0.0. The first P4 approach (ADR-054..059: hand-set multipliers, `ModelConfig`, `tune.py`, model 1.1.0 for RBs) was dropped. **Steps 1-2 done (2026-11-14):** P3 merged into `main` (PR #1, merge commit); branch `p4-model` rebased onto it, draft PR #3, CI green; the old model code removed, so the live model is the 1.0.0 method again (backtest reproduces 1.0.0 exactly), keeping the measuring tools (walk-forward backtest with `--compare` over named models in `backtest.MODELS`, `compare.py` bootstrap, startable slice, injury-game marking, stored lines/injury reports/snapshots, version-safe screens). **Step 3 done (2026-11-14):** nflverse data from 2016 (ADR-062), air yards, new tables `depth_chart_weeks` and `player_background` (ADR-063); fixed the daily refresh (2025+ injury files have no `date_modified`). **Step 4 done (2026-11-15):** `api/app/model/ml/features.py` builds the 116-column feature table (one row per player-week, nothing from kickoff on; leak test passes on synthetic and real data); `nfl_games.roof` added; old `features/` signal files deleted. **Step 5 done (2026-11-16):** `xgboost-cpu`, 27 targets (`ml/targets.py`), training with settings picked inside training seasons (`ml/train.py`), `python -m app.scripts.train_ml` → `docs/Build-Plan/ML-Training-Report.md`. **Step 6 done (2026-11-16):** `ml/project.py` (expected stats, minor stats, learned spreads, availability) and spread-aware `scoring.score(..., variance)` (ADR-064); first preview on 2025 full PPR startable: ML 6.17 vs 1.0.0 6.36. **Step 7 in progress:** four-season walk-forward (`python -m app.scripts.evaluate_ml`, about 52 minutes, keep the machine awake), ship rule passes in half, full and standard PPR; Sleeper's past projections as a local benchmark (ADR-066); availability fitted (ADR-068: Questionable and Doubtful projected as if they play less a fitted trim, with `p_play` and chance-weighted `expected`; `injury_reports.played` from snap counts), half PPR startable 5.47 against 1.0.0's 5.72 and Sleeper's 5.48; practice status in the chance he plays (ADR-069). The rest of P4 is planned with every owner decision made except the ship call (ADR-070..077; "Remaining work" in the P4 Build Plan). Next: step 7c, the tuning run (ADR-070). Local tooling: `python -m uv` (installed with pip). The P3 real-league check is partly seen (connect works; score match, waivers/trades/live on ESPN and expired cookies still open in Verification Gaps).
Backend change workflow: edit the API, then `python -m app.scripts.export_openapi` and
`npm run generate:api` (in `web/`), and commit `api/openapi.json` and the generated client together.
