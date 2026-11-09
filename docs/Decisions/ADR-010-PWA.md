---
title: "ADR-010: Responsive web app + PWA"
date: 2026-11-08
tags: [adr, frontend, platform]
status: accepted
---
# ADR-010: Responsive web app + PWA

## Options considered
| Option | Upside | Downside |
|---|---|---|
| **Responsive web + PWA** | One codebase for phone and desktop; installable; push notifications | Not in app stores |
| Web + native mobile (React Native) | Real iOS/Android apps | Roughly doubles frontend work; App Store fees and review |
| Native mobile only | App-store presence | Users must install it before trying it |

## Decision
A responsive web app that is also a **Progressive Web App**: installable to the home screen, with web push notifications for injuries and scores. See [PWA](../Concepts/PWA.md).

## Why
Anyone can open a link and use it immediately. Push notifications cover the main reason to want a native app.

Related: [PWA](../Concepts/PWA.md) · [ADR-012 Frontend](ADR-012-Frontend-NextJS.md) · [ADR-025 Navigation](ADR-025-Navigation-Bottom-Tabs.md)
