---
title: "ADR-018: AI assistant — tool-using agent + news RAG"
date: 2026-11-08
tags: [adr, ai, llm]
status: accepted
---
# ADR-018: AI assistant (P3) — Claude tool-using agent + news search (RAG)

## Context
The LLM doesn't know your league. It knows general football up to its training date, not your roster or this week's projections. The design question is how Sunday War Room gives it your data. Full explanation: [LLM Agents and RAG](../Concepts/LLM-Agents-and-RAG.md).

## Options considered — "Should I start Robinson or Pacheco this week?"
```
1 Prompt stuffing: backend pastes your roster + projections into the message → AI → answer
                   (blind to anything not pasted; may invent stats)
2 Agent:           AI calls get_projection("Robinson"), get_projection("Pacheco"), get_matchup(10)
                   → real Sunday War Room numbers → "Start Robinson: 17.1 vs 12.8 projected, softer defense…"
3 Agent + RAG:     same as 2, plus search_news("Pacheco") → "…and Pacheco was limited in practice."
```
| | 1 Prompt stuffing | 2 Agent | 3 **Agent + RAG** |
|---|---|---|---|
| Uses your real data | Partly | ✅ | ✅ |
| Makes up numbers | Often | Rarely | Rarely |
| Can explain *why* (news) | ❌ | ❌ | ✅ |
| Build effort | Low | Medium | High |
| Answers grounded in data | Weak | Strong | Strongest |

## Decision
**Option 3.**
- **Claude via the Anthropic API**, as a **tool-using agent**.
- Tools are Sunday War Room's own **read-only** functions: matchup, projections, waivers, trade analyzer, and `search_news`.
- **News RAG**: queue jobs ([ADR-016](ADR-016-Ingestion-Job-Queue.md)) ingest injury/news articles, create **embeddings**, and store them in PostgreSQL with **pgvector**. `search_news` retrieves the most relevant ones.
- **Per-user daily message limit** to control cost on a free product ([ADR-011](ADR-011-Monetization.md)).

## Guardrails (lessons from the old project)
- News is linked to players **by platform athlete id where available**, not by name matching in prose.
- When the agent cites news, it quotes the source text. A quote that isn't really in the article is dropped.
- News informs explanations; it does **not** change projected points until it has been measured to help (graded like any model change).

## Open sub-question
Which news sources to use (licensing, coverage): decided in the P3 spec. See [Open Questions](../Specs/Open-Questions.md).

Related: [LLM Agents and RAG](../Concepts/LLM-Agents-and-RAG.md) · [Features by Phase](../Specs/Features-by-Phase.md) · [ADR-015 PostgreSQL](ADR-015-Database-PostgreSQL.md)
