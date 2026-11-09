---
title: "ADR-041: Accessibility standard — WCAG 2.1 AA, checked automatically on every screen"
date: 2026-11-09
tags: [adr, accessibility, design, ui]
status: accepted
---
# ADR-041: Accessibility standard — WCAG 2.1 AA, checked automatically on every screen

## Context
[ADR-004](ADR-004-Production-Grade-Bar.md) sets a production-grade bar, and the [UI spec](../Specs/UI-Screens.md) promises touch targets of at least 44 px. Neither says how readable the text must be. When an automated accessibility checker (axe) was first run over every screen in both themes (P1 step 14), it found one kind of problem, in 9 of 10 screen-and-theme combinations: **text contrast below the WCAG AA minimum (4.5:1)**. The colors came from the mockup; the light theme had never been checked.

**This standard, and the color changes below, were decided while building P1 step 14.** They change the look slightly from mockup v3. Say so if you'd rather keep the exact mockup colors; the tokens are all in `web/src/app/globals.css`.

## Options considered
| | **A: WCAG 2.1 AA, enforced by tests** | B: Keep the mockup colors exactly | C: AAA (7:1) |
|---|---|---|---|
| Small grey labels readable in daylight, on cheap screens, with low vision | ✅ | ❌ (faint grey was 3.0:1 in dark, 2.5:1 in light) | ✅ |
| Matches mockup v3 | Very close (dark), a little darker (light) | Exactly | Noticeably different |
| Legal and store expectations for a public app | Meets the common bar | Risk | Exceeds |
| Cost | A one-time token change; a test keeps it | None now | Large palette change |

## Decision
**A.** Every screen is scanned by axe (WCAG 2.0/2.1 A and AA rules) in the dark and light themes by `web/e2e/accessibility.spec.ts`, and so is the offline page; any serious or critical finding fails the suite. Fixes were computed as the **smallest change per color** that reaches 4.5:1 on every surface it appears on, keeping hue and saturation.

| Token | Dark: before → after | Light: before → after |
|---|---|---|
| `ink-lo` (secondary text) | `#8d99a6` → `#8f9ba8` | `#66717d` → `#59626d` |
| `ink-faint` (small labels) | `#5c6a78` → `#808f9e` | `#98a1aa` → `#616b75` |
| `accent` (gold) | unchanged | `#a8761c` → `#6f4e13` |
| `good`, `bad`, `warn`, `ember` (text) | `ember` `#e2683c` → `#e5764e` (the Live chip tint is also lighter) | `#13915e` → `#0d5f3e`, `#d23a4b` → `#9c2431`, `#c06a12` → `#7e450c`, `#c24e22` → `#973d1a` |
| Position labels used as text | unchanged | darker text versions (for example WR `#60a5fa` → `#065dc7`); the bright colors stay on the tags |
| Bench tag background, opponent badge | `#64748b` → `#6d7d96`; `#c4566f` → `#c14e69` | same |

In the dark theme the secondary and faint greys are now close in brightness, so there are three readable text levels, not four. The week-stepper arrows and the logo link also got 44 px touch areas without changing how the header looks.

## Why
Small grey text that cannot be read is a defect, not a style. Doing it with a computed minimum change and a test that guards it keeps the look and keeps the problem from coming back.

## Trade-offs accepted
Automated checks find roughly a third of accessibility problems. Keyboard-only use and a screen reader still need a human ([Verification Gaps](../Build-Plan/Verification-Gaps.md) V-29). The light theme's gold accent is now a dark bronze.

Related: [ADR-032 Visual style](ADR-032-Visual-Sunday-War-Room-Style.md) · [ADR-024 Theme](ADR-024-Theme-Dark-First.md) · [ADR-040 E2E tests](ADR-040-End-to-End-Test-Approach.md) · [UI Screens](../Specs/UI-Screens.md)
