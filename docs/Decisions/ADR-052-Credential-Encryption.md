---
title: "ADR-052: Platform credentials are encrypted by the app with a key from the environment"
date: 2026-11-10
tags: [adr, security]
status: accepted
---
# ADR-052: Credential encryption

## Context
ESPN cookies (and, later, Yahoo tokens) work like passwords. A leaked database backup must not expose them.

## Options considered
| | App-level key (Fernet) | Database (pgcrypto) |
|---|---|---|
| Stolen backup | Gibberish | Gibberish |
| Key location | Secret environment setting | Sent with every query |
| Key could leak into logs | No | Yes |
| Key rotation | Built in (`MultiFernet`) | Manual re-encryption |
| Testing | Plain unit tests | Needs a real Postgres |

## Decision
**The API encrypts with Fernet (the `cryptography` library) before saving.** `CREDENTIALS_KEYS` holds one or more keys; the first encrypts, every listed key can decrypt, so a new key can be added and old data re-encrypted by a rotation script. The app refuses to start in production with the development key, as it does for the JWT secret.

Rules that go with it:
- Cookies are never passed as background-job arguments (the job queue stores arguments in Redis as plain text); the API saves them and enqueues only the account id.
- Cookies are never written to logs (a log filter blanks `espn_s2` and `SWID`), never returned by an API response, and never committed in test fixtures.
- Disconnecting deletes the stored ciphertext.

Limit: an attacker who controls the running server can read the key. Encryption protects backups and database access, not a compromised server.

Related: [ADR-051](ADR-051-ESPN-Access-Link-First-Cookie-Fallback.md) · [ADR-016 Ingestion](ADR-016-Ingestion-Job-Queue.md) · [Data Model](../Specs/Data-Model.md)
