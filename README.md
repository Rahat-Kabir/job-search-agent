# Job Search Agent

Upload your CV, and the agent reads your skills, searches the web for matching jobs, and ranks them by how well they fit your profile , all through a simple chat interface.

Built on [LangChain DeepAgent](https://docs.langchain.com/oss/python/deepagents/overview) — a framework that lets an AI orchestrator delegate tasks to specialized sub-agents, each with their own tools, so the system can parse CVs, search the web, and rank results as separate focused steps.

**Key Features:**
- Upload a CV and get a structured profile (skills, experience, job titles) extracted automatically
- Searches multiple job sources across the web simultaneously
- Ranks and scores every job by how well it matches your profile
- Chat-based UI — ask follow-up questions, refine search criteria, upload new CVs mid-conversation

## Quickstart

```bash
# 1. Install dependencies
uv sync

# 2. Copy env file and add your API keys
cp .env.example .env          # Linux/macOS
Copy-Item .env.example .env   # Windows PowerShell

# 3. Fill in required keys in .env:
#    DEEPSEEK_API_KEY=your_key
#    TAVILY_API_KEY=your_key

# 4. Start PostgreSQL + Redis
docker compose up -d

# 5. Start backend (http://127.0.0.1:8020)
uv run uvicorn backend.api:app --reload --host 127.0.0.1 --port 8020

# 6. Start frontend (http://localhost:5173)
cd frontend && npm install && npm run dev
```

## CLI Usage

```bash
uv run python main.py "path/to/cv.pdf"
```

The agent will:
1. Parse your CV and extract skills/experience
2. Show profile summary for confirmation
3. Search for matching jobs via Tavily, Brave, Firecrawl
4. Display ranked results with match scores

The frontend runs on `http://localhost:5173` and is also served as static files by FastAPI in production (`npm run build` output).

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/chat` | POST | — | Send message, get response |
| `/chat/stream` | POST | — | SSE streaming response |
| `/chat/upload` | POST | — | Upload CV in chat context (returns `user_id`) |
| `/chat/{session_id}` | GET | — | Get chat history |
| `/cv/upload` | POST | — | Upload PDF CV, returns extracted profile + `user_id` |
| `/profile` | GET | `X-User-ID` | Get current user profile |
| `/preferences` | GET/PUT | `X-User-ID` | Get or update search preferences |
| `/search` | POST | `X-User-ID` | Start background job search |
| `/search/results` | GET | `X-User-ID` | Poll search results |

**How to get a `user_id`:** Upload a CV via `POST /cv/upload` or `POST /chat/upload`. The response includes a `user_id` — use it as the `X-User-ID` header for profile, preferences, and search endpoints.

## Architecture

### System Overview

```
┌─────────────────┐      ┌──────────────┐      ┌────────────────────┐
│  React Frontend │ ───→ │  FastAPI API  │ ───→ │  AI Agent System   │
│  (Vite + TW)    │ ←─── │  (REST + SSE) │ ←─── │  (DeepAgents/LG)   │
└─────────────────┘      └──────┬───────┘      └────────┬───────────┘
                                │                       │
                     ┌──────────┴──────────┐   ┌───────┴────────┐
                     │  PostgreSQL  │ Redis │   │ Tavily │ Brave │
                     │  (data)      │(rate) │   │ Firecrawl      │
                     └──────────────┴──────┘   └────────────────┘
```

### Agent System

The core is an **Orchestrator agent** (`backend/agents/orchestrator.py`) built on DeepAgents + LangGraph, powered by DeepSeek LLM (temperature 0.1 for deterministic output).

**Intent detection** — the orchestrator classifies every user message into one of four intents:

| Intent | Action |
|--------|--------|
| `CV_UPLOAD` | Delegate to **CV Parser** sub-agent |
| `SEARCH_JOBS` | Delegate to **Job Searcher** sub-agent |
| `REFINE` | Re-run job search with updated criteria |
| `CHAT` | Respond directly (no sub-agent needed) |

**Sub-agents:**

- **CV Parser** (`backend/agents/cv_parser.py`) — takes raw PDF text, outputs a compact JSON profile: `{skills[], experience_years, titles[], summary}`. Constrained to top-10 skills, max 3 titles, 30-word summary.

- **Job Searcher** (`backend/agents/job_searcher.py`) — has three tools:
  1. **Tavily Search** — primary web search
  2. **Brave Search** — backup/alternative
  3. **Firecrawl** — deep-scrapes the top 3 job posting URLs for full content

  Returns up to 10 jobs scored 0-100 with match reasons.

**State persistence** — each chat session gets a `thread_id` and the orchestrator uses LangGraph's `MemorySaver` to maintain conversation context across turns.

### Data Flow

#### CV Upload → Profile Extraction
```
PDF file → PyPDF text extraction → truncate to 4000 chars
  → Orchestrator → CV Parser sub-agent → JSON profile
  → Save to PostgreSQL (User + Profile + Preferences)
  → Return profile to frontend
```

#### Chat-Driven Job Search (SSE Streaming)
```
User message → POST /chat/stream
  → Orchestrator detects SEARCH_JOBS intent
  → Job Searcher sub-agent runs web searches
  → Scrapes top 3 URLs via Firecrawl
  → Scores & ranks jobs against user profile
  → Streams status updates back via SSE
  → Returns ranked job array → rendered as JobCards
```

### Chat Architecture
```
User Message → /chat endpoint → Orchestrator (intent detection)
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                 ↓                 ↓
              CV Upload          Job Search         Chat/Q&A
              (cv-parser)      (job-searcher)     (direct response)
```

### Frontend

React SPA with a chat-first interface. Design system: "Apple Calm" — flat indigo accent (#5856D6), Outfit + DM Sans typography, dark/light mode.

```
Chat.jsx (main container, SSE streaming, session management)
├── Sidebar.jsx        — chat session history, new chat, delete
├── ChatMessage.jsx    — renders text (markdown), job cards, or profile
│   └── JobCard.jsx    — score ring (SVG), match reason, bookmark, apply CTA
└── ChatInput.jsx      — message input, drag-and-drop PDF upload
```

- **SSE streaming** — real-time status updates while agent processes
- **Session persistence** — localStorage for session list, API for message history
- **Responsive** — collapsible sidebar with backdrop overlay on mobile

### Database Schema

```
User ──┬── Profile (1:1)        skills, experience, cv_text
       ├── Preferences (1:1)    location_type, target_roles, min_salary
       ├── SearchSession (1:N)  status progression, results
       │     └── JobResult (1:N)  title, company, score, url
       └── ChatSession (1:N)    thread_id for agent state
             └── ChatMessage (1:N)  role, content, message_type, extra_data
```

Search status progression: `pending → analyzing_profile → searching_jobs → ranking_results → completed`

### Security

- **CORS** — origins restricted via `CORS_ORIGINS` env var
- **Rate limiting** — Redis-backed via slowapi (5 req/min chat, 3 req/min uploads)
- **File size limit** — 5 MB max for PDF uploads

### Why Sub-Agent Architecture?

We intentionally chose a **hierarchical sub-agent design** over a simpler single-agent approach:

| Aspect | Single Agent | Sub-Agent Architecture |
|--------|--------------|------------------------|
| Control | Limited | Fine-grained per task |
| Extensibility | Hard to add features | Add new sub-agents easily |
| Debugging | Opaque | Isolated, testable units |
| Model flexibility | One model for all | Different models per sub-agent |
| Future expansion | Major refactor needed | Plug-in new capabilities |

**Trade-off**: Higher token usage (~30-50% more) due to context passing between agents. We mitigate this with:
- Context trimming (orchestrator sends only compact data to sub-agents)
- Compact JSON-only outputs (no verbose prose)
- CV truncation (max 4000 chars)

### Robust Response Parsing

**Why not regex?** LLM outputs are unpredictable. Regex-based parsing fails when:
- Model wraps JSON in markdown blocks (`` ```json ``)
- Model adds explanatory text before/after JSON
- Field names vary (`job_title` vs `title` vs `position`)
- Formatting changes between model versions

**Our solution** (`backend/utils/parser.py`):
- Multiple extraction strategies (clean JSON → fenced blocks → bracket matching)
- Markdown fallback for non-JSON responses
- Field normalization (handles variant names)
- Graceful degradation (always returns valid structure)

### Tech Stack

**[LangChain DeepAgent](https://python.langchain.com/docs/concepts/deep_agents/)** — Provides:
- **Middleware** — request/response processing pipeline
- **Sub-agents** — specialized agents for CV parsing and job searching
- **AgentHarness** — orchestration and lifecycle management
- **File system** — document handling and state persistence

**[DeepSeek-V3](https://www.deepseek.com/)** — Cost-effective LLM choice:
- Comparable performance to GPT-4 at significantly lower cost
- Ideal for multi-agent architectures where token usage multiplies

## Environment Variables

```
DEEPSEEK_API_KEY=       # Required
TAVILY_API_KEY=         # Required
BRAVE_API_KEY=          # Optional
FIRECRAWL_API_KEY=      # Optional
LANGSMITH_API_KEY=      # Optional (for tracing)
DATABASE_URL=           # Optional (for persistence)
```

## Known Limitations

- **Token usage** — elevated due to sub-agent context passing (~30-50% overhead), mitigated by trimming and compact outputs
- **Session memory** — agent state stored in-memory (`MemorySaver`), lost on server restart; production would need a persistent checkpointer