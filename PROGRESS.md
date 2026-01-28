# Implementation Progress

## Phase 1: Core Agents
| Task | Status |
|------|--------|
| Project setup | Done |
| PDF parser tool | Done |
| CV Parser sub-agent | Done |
| Tavily search tool | Done |
| Brave search tool | Done |
| Firecrawl tool | Done |
| Job Searcher sub-agent | Done |
| Orchestrator agent | Done |
| CLI test | Done |

---

## Phase 2: API & Persistence
| Task | Status |
|------|--------|
| Docker + PostgreSQL | Done |
| FastAPI app | Done |
| POST /cv/upload | Done |
| GET /profile | Done |
| PUT /preferences | Done |
| POST /search | Done |
| GET /search/results | Done |

---

## Optimizations Applied
1. CV Truncation (max 4000 chars)
2. Compact prompts (JSON-only output)
3. Selective scraping (top 3 only)
4. State persistence (checkpointer + thread_id)

---

## Known Issue
**High token usage** (~370K tokens) due to Deep Agents sub-agent architecture.

Each sub-agent receives full context, multiplying tokens. Options:
1. Switch to single-agent with tools (no sub-agents)
2. Use cheaper model for sub-agents
3. Accept cost for research-grade results
