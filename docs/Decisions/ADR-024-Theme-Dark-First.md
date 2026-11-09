---
title: "ADR-024: Theme — dark-first with light toggle"
date: 2026-11-08
tags: [adr, design, ui]
status: accepted
---
# ADR-024: Theme — dark-first, with a light toggle

## Options considered
Dark-first + light toggle · Follow system setting only (no in-app toggle) · Dark only (one theme to design and test).

## Decision
**Dark by default**, with a light-mode toggle, and the phone's system setting is respected on first visit. Implemented with Tailwind's `dark:` variant over semantic tokens ([ADR-032](ADR-032-Visual-Sunday-War-Room-Style.md)), so both themes come from one set of components.

## Why
Dark suits game-day and night-time phone use and the storm-blue Sunday War Room look ([ADR-032](ADR-032-Visual-Sunday-War-Room-Style.md)). Light mode serves daylight readers at little extra cost.

Related: [ADR-032 Visual style](ADR-032-Visual-Sunday-War-Room-Style.md) · [UI Screens](../Specs/UI-Screens.md)
