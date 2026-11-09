---
title: "LLMs, tool-using agents and RAG"
date: 2026-11-08
tags: [concept, ai, llm]
---
# LLMs, tool-using agents and RAG

## LLM via API
An **LLM** (large language model, like Claude) is reached through an **API**: the backend sends text and gets text back, paying a small amount per message based on length. The LLM **doesn't know your league**; it knows general football up to its training date.

## Three ways to give it your data
1. **Prompt stuffing:** paste your roster and projections into every message. Simple, but blind to anything not pasted, expensive with lots of data, and prone to inventing numbers.
2. **Tool-using agent:** give the model a list of **tools**, your own functions like `get_matchup(week)` or `get_projection(player)`. The model decides which to call, the backend runs them, and the model answers using real results. It can call several in a row: that loop is what makes it an "agent."
3. **Agent + RAG (Sunday War Room's choice):** add a `search_news` tool backed by **retrieval-augmented generation**: look up relevant text first, then answer with it.

## How RAG works
1. **Ingest:** a job fetches news/injury articles.
2. **Embed:** each article (or chunk) becomes an **embedding**, a list of numbers capturing its meaning. Similar meanings have nearby numbers.
3. **Store:** embeddings go into PostgreSQL with **pgvector**.
4. **Retrieve:** for "Is Pacheco playing?", embed the question, find the closest articles, and hand them to the model.

## Side by side: "Should I start Robinson or Pacheco?"
```
Prompt stuffing: paste whole roster → AI → answer (may invent stats)
Agent:           get_projection("Robinson"), get_projection("Pacheco"), get_matchup(10)
                 → "Start Robinson: 17.1 vs 12.8 projected, softer defense."
Agent + RAG:     … + search_news("Pacheco") → "…and Pacheco was limited in Thursday practice."
```

## Sunday War Room guardrails
- Tools are **read-only**: the agent can't change anything.
- **Per-user daily message limit** controls cost.
- News is attributed to players **by platform athlete id** where possible, never by fuzzy name matching.
- Cited news must quote the real article text.
- News explains; it does **not** move projections until measured to help.

Related: [ADR-018](../Decisions/ADR-018-AI-Agent-With-RAG.md) · [Databases (pgvector)](Databases.md) · [Job Queues](Job-Queues-and-Redis.md)
