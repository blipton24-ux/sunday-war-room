---
title: "ADR-017: Auth — Auth.js with Google + magic links"
date: 2026-11-08
tags: [adr, auth, security]
status: accepted
---
# ADR-017: Auth — Auth.js (Google sign-in + email magic links)

## Context
A public product needs sign-up/login (**authentication**: who are you?) and per-user data isolation (**authorization**: what may you see?). Authorization is the same whichever option is picked: every row has a `user_id` checked on every request. Full explanation: [Auth, OAuth and Tokens](../Concepts/Auth-OAuth-Tokens.md).

## Options considered — a new user signs up with Google
```
1 Clerk:   Clerk's sign-in box → Google → user stored in Clerk → Clerk token → FastAPI verifies with Clerk's key
2 Auth.js: "Sign in with Google" → Google → user stored in YOUR Postgres → signed token cookie → FastAPI verifies with shared secret
3 DIY:     hand-written OAuth flow, or email+password with hashing, tokens, reset emails…
```
| | 1 Managed (Clerk) | 2 **Auth.js** | 3 DIY |
|---|---|---|---|
| Setup effort | Lowest | Medium | Highest |
| Security risk | Lowest | Low | Highest |
| Cost at scale | Paid past free tier | Free | Free |
| Who owns user data | Vendor | You | You |
| Security pieces understood in-house | Few (hidden by vendor) | OAuth + signed tokens, configured | All, hand-written |

## Decision
**Auth.js** in Next.js, with **Google sign-in** and **email magic links** (no passwords stored). Users and sessions live in PostgreSQL. Auth.js issues a signed token, and **FastAPI verifies it** with a shared secret on every request and derives `user_id` from it.

## Why
Free at any scale, you own the data, and you configure (and can explain) the security pieces without hand-writing the dangerous parts.

## Trade-offs accepted
The token handoff between Next.js and FastAPI must be done carefully. Both sit on the same site (`ffcc.app` / `api.ffcc.app`) so cookies work. Magic links require an email-sending service (see [Open Questions](../Specs/Open-Questions.md)).

Related: [Auth, OAuth and Tokens](../Concepts/Auth-OAuth-Tokens.md) · [Multi-Tenancy](../Concepts/Multi-Tenancy.md) · [ADR-005 Public product](ADR-005-Public-Multi-Tenant.md)
