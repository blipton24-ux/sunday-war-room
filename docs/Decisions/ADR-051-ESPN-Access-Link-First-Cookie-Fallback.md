---
title: "ADR-051: ESPN access: league link first, guided cookie paste for private leagues"
date: 2026-11-10
tags: [adr, integrations, security]
status: accepted
---
# ADR-051: ESPN access

## Context
ESPN has no "sign in with ESPN" for other apps. A private league can only be read with the two cookies a signed-in browser holds: `SWID` (which account) and `espn_s2` (proof of sign-in, valid for months). A web page cannot read another site's cookies, and `espn_s2` is HttpOnly, so even code running on espn.com cannot read it. Closes [Open Question](../Specs/Open-Questions.md) #12.

## Options considered
| Option | Effort for the user | Build effort | Catch |
|---|---|---|---|
| Public league + link | Paste a link | Small | Only if the commissioner made the league viewable |
| **Guided cookie paste** | A few minutes, once a season, on a computer | Small | Clunky; not possible on a phone |
| Browser extension | One click | Large | A second project; Chrome/Edge desktop only |
| Remote browser | Log in in a window | Very large | Password passes through our server; ESPN may block it |
| ESPN password | Type it | Large | We would hold a password; captchas and 2-step break it |

## Decision
**Link first, guided paste as the fallback.**
1. The user pastes a league link. The server asks ESPN once with no cookies. A public league connects immediately and the user picks their team.
2. If ESPN says the league is private, a guided screen shows how to copy `espn_s2` and `SWID` (steps and pictures per browser). With cookies the app lists every ESPN football league the account belongs to and preselects the user's own team.
3. On a phone the cookie step cannot be done, so the screen offers **"Email me a link to finish on a computer"** (sent through the existing email provider, [ADR-029](ADR-029-Email-Resend.md), rate-limited).
4. A browser extension is a backlog item.

**Shared private leagues:** a user's cookies are used **only for that user's own view**. If they expire, that user's league pauses and a reconnect banner appears; another member's cookies are never used on their behalf.

**Expired cookies:** the account is marked `needs_reconnect`; syncs for it stop until the user pastes new ones.

## Why
Public leagues need nothing stored. For private leagues, a user-supplied cookie pair is the only method that does not mean handling a password or building a second product, and it stores less than any alternative. Using only the owner's own cookies keeps each user's access limited to what that user already has.

Related: [ADR-052 Credential encryption](ADR-052-Credential-Encryption.md) · [ADR-053 ESPN client](ADR-053-ESPN-Client-Own-Code.md) · [ADR-006](ADR-006-Platform-Adapters.md) · [Adapter Pattern](../Concepts/Adapter-Pattern.md)
