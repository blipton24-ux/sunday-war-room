---
title: "ADR-011: Free v1, room for a paid tier"
date: 2026-11-08
tags: [adr, product, business]
status: accepted
---
# ADR-011: Free in v1, designed so a paid tier can be added

## Options considered
Free but payment-ready · Paid tier from day one (Stripe subscriptions, webhooks; legal and tax overhead) · Always free.

## Decision
No payments in v1. The design leaves room: a `plan` field on users and feature checks in one place, so something like "AI chat beyond N messages/day" could become a paid feature later without restructuring.

## Why
Keeps the focus on engineering. A Stripe integration can be its own later phase if wanted.

## Knock-on effects
Hosting choices consider commercial-use terms ([ADR-022](ADR-022-Hosting-Container-Platform.md)), and AI usage is capped per user ([ADR-018](ADR-018-AI-Agent-With-RAG.md)).

Related: [ADR-005 Public product](ADR-005-Public-Multi-Tenant.md) · [Data Model](../Specs/Data-Model.md)
