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
| | Managed (Clerk) | **Self-hosted library (Auth.js, Better Auth)** | DIY |
|---|---|---|---|
| Setup effort | Lowest | Medium | Highest |
| Security risk | Lowest | Low | Highest |
| Cost at scale | Paid past free tier | Free | Free |
| Who owns user data | Vendor | You | You |

The self-hosted column was first filled by Auth.js ([ADR-017](../Decisions/ADR-017-Auth-AuthJS.md)); Sunday War Room uses **Better Auth** ([ADR-035](../Decisions/ADR-035-Auth-Better-Auth.md)), because Auth.js now receives security fixes only.

## Sunday War Room's flow
```
"Sign in with Google" → Google → Better Auth (inside Next.js) saves the user in PostgreSQL
→ session id in an HttpOnly cookie
→ the browser asks Next.js for data (/api/v1/...); Next.js checks the session and
  attaches a 15-minute signed token ("user 7") when it calls FastAPI
→ FastAPI verifies the signature, reads user_id, scopes every query to it
```
Two different things are called "token" here: the **session cookie** (browser ↔ Next.js, long-lived, just an id looked up in the database) and the **API token** (Next.js ↔ FastAPI, short-lived, signed, never sent to the browser: [ADR-036](../Decisions/ADR-036-API-Access-Through-Web-Server.md)).

## Security basics worth knowing
- **HttpOnly** cookies can't be read by page JavaScript, which blunts XSS attacks.
- **SameSite** cookies help block CSRF (other sites making requests as you).
- Never trust the frontend for authorization; the API checks ownership itself.

Related: [ADR-035](../Decisions/ADR-035-Auth-Better-Auth.md) · [ADR-036](../Decisions/ADR-036-API-Access-Through-Web-Server.md) · [ADR-017](../Decisions/ADR-017-Auth-AuthJS.md) · [Multi-Tenancy](Multi-Tenancy.md)
