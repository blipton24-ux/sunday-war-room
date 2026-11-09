---
title: "Progressive Web App (PWA)"
date: 2026-11-08
tags: [concept, frontend, mobile]
---
# Progressive Web App (PWA)

A PWA is a website that can behave like an installed app:
- **Installable:** "Add to Home Screen" puts an icon on your phone that opens full-screen without browser bars.
- **Push notifications:** "Your RB was ruled OUT" arrives even when the app is closed.
- **Fast/offline-tolerant:** cached screens load instantly and show the last data if the connection drops.

## The pieces
- **Web app manifest** (`manifest.json`): name, icons, colors, start URL. It tells the phone how to install it.
- **Service worker:** a small script the browser runs in the background. It caches files and receives push messages.
- **Web Push:** the backend sends a message to the browser's push service (using VAPID keys), which wakes the service worker to show a notification.

## In Sunday War Room
P1 ships the manifest and service worker (installable). P2 adds push alerts, sent by a worker job ([Job Queues](Job-Queues-and-Redis.md)). iPhones support web push only for PWAs **installed to the home screen**, so the app should prompt iPhone users to install.

Related: [ADR-010](../Decisions/ADR-010-PWA.md) · [TypeScript, React, Next.js](TypeScript-React-NextJS.md)
