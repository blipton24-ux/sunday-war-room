---
title: "Auth — authentication, authorization, OAuth and tokens"
date: 2026-11-08
tags: [concept, auth, security]
---
# Auth: authentication, authorization, OAuth and tokens

## Two different words
- **Authentication:** "who are you?" Proving you are who you say (Google login, email link).
- **Authorization:** "what are you allowed to see?" Once Sunday War Room knows who you are, it shows only *your* leagues. Every row has an owner (`user_id`), and the backend checks it on every request.

## How login works in any web app
1. You prove who you are.
2. The server gives your browser a **token**, a signed digital pass ("this is user 1, valid until Friday"), usually in a **cookie** the browser sends automatically.
3. Every later request carries the token. The backend checks the **signature** (so it can't be forged) and knows it's you.

A common token format is a **JWT** (JSON Web Token): readable data plus a cryptographic signature.

## OAuth ("Sign in with Google")
Instead of Sunday War Room storing a password, Google confirms who you are and tells Sunday War Room. You never give Sunday War Room your Google password. Sunday War Room also uses OAuth in P4 to connect **Yahoo** leagues.

## Magic links
"Email me a sign-in link": a one-time link that logs you in. No password to store, leak or reset.

## The three options compared
| | Managed (Clerk) | **Auth.js** | DIY |
|---|---|---|---|
| Setup effort | Lowest | Medium | Highest |
| Security risk | Lowest | Low | Highest |
| Cost at scale | Paid past free tier | Free | Free |
| Who owns user data | Vendor | You | You |

## Sunday War Room's flow (Auth.js)
```
"Sign in with Google" (Next.js / Auth.js) → Google → Auth.js saves user in PostgreSQL
→ signed token in an HttpOnly cookie → Next.js calls FastAPI with the token
→ FastAPI verifies the signature, reads user_id, scopes every query to it
```

## Security basics worth knowing
- **HttpOnly** cookies can't be read by page JavaScript, which blunts XSS attacks.
- **SameSite** cookies help block CSRF (other sites making requests as you).
- Never trust the frontend for authorization; the API checks ownership itself.

Related: [ADR-017](../Decisions/ADR-017-Auth-AuthJS.md) · [Multi-Tenancy](Multi-Tenancy.md)
