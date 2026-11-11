---
title: "ADR-050: Yahoo becomes P7, deploy and push alerts become P8"
date: 2026-11-10
tags: [adr, process, planning]
status: accepted
---
# ADR-050: Yahoo moves to its own phase before deployment

## Context
[ADR-049](ADR-049-Phases-Reordered-ESPN-First.md) put ESPN and Yahoo together in P3. ESPN is the platform the owner's own league uses, so it is what the rest of the app gets tested on. Yahoo can only be verified end to end with a Yahoo account in a Yahoo league, and Yahoo's sign-in requires an https return address, which a local setup does not have.

## Options considered
| Option | Meaning |
|---|---|
| ESPN + Yahoo together in P3 | One adapter phase; Yahoo built without a real account to test against |
| **ESPN in P3, Yahoo later, just before deploy** | P3 stays focused on the platform used for testing; Yahoo is built close to the point where a real https address exists |

## Decision
| Phase | Scope |
|---|---|
| P3 | ESPN adapter |
| P4 | Improved model projections |
| P5 | AI assistant + strategy tendencies |
| P6 | UI/UX overhaul |
| **P7** | **Yahoo adapter** (OAuth sign-in, token refresh, scoring coverage) |
| **P8** | **Deploy + push alerts** |

Amends the phase table in [ADR-049](ADR-049-Phases-Reordered-ESPN-First.md). The adapter work in P3 (a platform registry, platform-neutral sync, encrypted credential storage) is built so that Yahoo only adds an adapter and an OAuth flow.

## Why
Yahoo's OAuth needs an https redirect address and a real Yahoo league to check against. Building it right before deployment puts it next to the phase that provides both.

Related: [ADR-049](ADR-049-Phases-Reordered-ESPN-First.md) · [ADR-042](ADR-042-Deploy-As-Phase-5.md) · [ADR-006 Platform adapters](ADR-006-Platform-Adapters.md) · [Features by Phase](../Specs/Features-by-Phase.md)
