---
title: "ADR-029: Magic-link email via Resend"
date: 2026-11-08
tags: [adr, auth, email]
status: accepted
---
# ADR-029: Magic-link emails are sent through Resend

## Context
Auth.js magic links ([ADR-017](ADR-017-Auth-AuthJS.md)) need a **transactional email service**. Mail sent straight from an app server usually lands in spam. Every option needs DNS records (SPF/DKIM) on Sunday War Room's domain to prove the mail is authentic.

## Options considered — a new user types their email and clicks "Email me a link"
```
Resend:      Auth.js → Resend API → inbox in seconds        (developer-focused; simple setup)
Postmark:    Auth.js → Postmark API → inbox in seconds      (best-in-class deliverability)
Amazon SES:  Auth.js → AWS SES → inbox                      (cheapest at scale; AWS setup + sandbox approval)
Google-only: no email sign-in in P1; "Sign in with Google" only
```
| | **Resend** | Postmark | Amazon SES | Google-only (P1) |
|---|---|---|---|---|
| Setup effort | Low | Low | High | None |
| Free tier* | Yes | Small | Pay-as-you-go | N/A |
| Deliverability | Good | Best | Good once configured | N/A |
| Users without Google can sign up | ✅ | ✅ | ✅ | ❌ |
| Auth.js support | Built-in provider | ✅ | ✅ | ✅ |

\* Current limits to be confirmed at setup.

## Decision
**Resend**, via Auth.js's built-in Resend provider. The API key lives only in environment secrets. DNS records (SPF, DKIM, and a DMARC policy) are added when the domain is chosen ([Open Questions](../Specs/Open-Questions.md) #2).

## Trade-offs accepted
One more external account and secret. Local development logs magic links to the console instead of sending real email.

Related: [ADR-017 Auth](ADR-017-Auth-AuthJS.md) · [Auth, OAuth and Tokens](../Concepts/Auth-OAuth-Tokens.md)
