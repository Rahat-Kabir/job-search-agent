# Technical Specification

## Agent Architecture

### Framework Stack
- **DeepAgents** (`deepagents>=0.1.0`) — hierarchical agent orchestration
- **LangChain** (`langchain>=0.3.0`) — tool decorators, middleware
- **LangGraph** (`langgraph>=0.2.0`) — state graph, checkpointing, interrupts
- **LangChain DeepSeek** (`langchain-deepseek>=0.1.0`) — LLM provider

### Agent Hierarchy
```
Orchestrator (intent routing, no tools)
├── cv-parser (pure LLM, no tools)
│   └── Returns: {skills, experience_years, titles, summary}
├── quick-searcher (Phase 1: fast search, no scraping)
│   ├── tavily_search
│   ├── brave_search
│   └── Returns: [{title, company, score, reason, url, location}] (max 15)
└── detail-scraper (Phase 2: deep scrape selected jobs)
    ├── firecrawl_scrape
    └── Returns: [{url, salary, description, requirements, benefits}]
```

### DeepAgent Features Used
- `create_deep_agent(backend=CompositeBackend(...))` — multi-route storage (default, /memories/, /workspace/)
- `create_deep_agent(memory=[AGENTS_MD])` — agent memory file loaded into system prompt
- `agent.astream(stream_mode="values")` — real-time streaming of agent events
- Built-in `SummarizationMiddleware` — auto-compresses long conversations at 85% context
- Built-in `TodoListMiddleware` — agent plans multi-step tasks
- `SubAgentMiddleware` — isolated context per sub-agent (auto-included)
- `interrupt_on` — HITL approval for search/scrape tools

### Storage Backends (CompositeBackend)
- `default` → `FilesystemBackend(.agent_data/)` — ephemeral scratch
- `/memories/` → `FilesystemBackend(.agent_data/memories/)` — persistent memories
- `/workspace/` → `FilesystemBackend(.agent_data/workspace/)` — persistent search results

### LLM Configuration
- **Model**: `deepseek-chat` (DeepSeek-V3)
- **Temperature**: 0.1 (deterministic for JSON output)
- **API Key**: `DEEPSEEK_API_KEY` env var

---

## State Persistence

### PostgreSQL Checkpointer
- **Package**: `langgraph-checkpoint-postgres>=2.0.0`
- **Class**: `PostgresSaver` (sync, uses `psycopg` connection pool)
- **Connection**: Reuses `DATABASE_URL` from app config
- **Lifecycle**: Managed by `backend/agents/checkpointer.py`
  - `init_checkpointer()` — creates connection pool + checkpoint tables
  - `get_checkpointer()` — returns singleton instance
  - `close_checkpointer()` — closes pool on shutdown
- **Integration**: Passed to `create_deep_agent(checkpointer=...)` in orchestrator

### Thread Management
- Each chat session has a unique `thread_id` (UUID)
- Stored in `ChatSession.thread_id` column
- Used in agent config: `{"configurable": {"thread_id": "..."}}`
- Enables conversation continuity across server restarts

### Agent Session Cache
- **Cache**: `cachetools.TTLCache(maxsize=200, ttl=3600)` — bounded, auto-evicting
- Avoids re-creating agent objects for active sessions
- Evicted agents are transparently recreated; checkpointer restores state from PostgreSQL

### SSE Generator DB Sessions
- Each SSE generator (`/stream`, `/confirm`, `/get-details`) creates its own `Session` via `next(get_db())`
- Prevents session-lifetime mismatch: FastAPI's `Depends(get_db)` cleanup can run before the generator finishes
- Each generator has `finally: gen_db.close()` for guaranteed cleanup

---

## Human-in-the-Loop (HITL)

### Configuration
```python
SEARCH_TOOL_INTERRUPT = {
    "tavily_search": {
        "allowed_decisions": ["approve", "reject"],
        "description": "Job search will call external APIs (Tavily).",
    },
    "brave_search": {
        "allowed_decisions": ["approve", "reject"],
        "description": "Backup search will call Brave API.",
    },
    "firecrawl_scrape": {
        "allowed_decisions": ["approve", "reject"],
        "description": "Web scraping will fetch job posting details.",
    },
}
```

### Mechanism
1. Passed to `create_deep_agent(interrupt_on=SEARCH_TOOL_INTERRUPT)`
2. DeepAgents injects `HumanInTheLoopMiddleware` for each tool
3. Middleware propagated to sub-agents via `SubAgentMiddleware`
4. When tool is called → LangGraph `interrupt()` fires
5. `agent.invoke()` returns with `result["__interrupt__"]`
6. Resume: `agent.invoke(Command(resume=True/False), config=config)`

### Auto-Approve Logic
- First interrupt in a search session: requires user confirmation
- Subsequent interrupts (e.g., brave_search after tavily_search): auto-approved
- Background search (`POST /search`): all interrupts auto-approved

---

## API Structure

### Chat Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Send message, get response (non-streaming) |
| `/chat/stream` | POST | SSE streaming response |
| `/chat/confirm` | POST | Approve/reject HITL interrupt (SSE streaming) |
| `/chat/get-details` | POST | Get detailed info for selected jobs (SSE streaming) |
| `/chat/upload` | POST | Upload CV in chat context |
| `/chat/sessions` | GET | List all sessions with title/preview |
| `/chat/{session_id}` | GET | Get chat history |
| `/chat/{session_id}` | DELETE | Delete session, messages, and in-memory agent |

### SSE Events
| Event | Description |
|-------|-------------|
| `status` | Initial status: `{stage, message}` |
| `agent_event` | Real-time agent event: `{type, tools?, message}` (tool_call, tool_result, auto_approve) |
| `confirmation` | HITL interrupt: `{session_id, requires_confirmation, message}` |
| `done` | Final response: `{session_id, user_id, message}` |
| `error` | Error: `{message}` |

### Streaming Architecture
- **Method**: `agent.astream(stream_mode="values")` — yields state after each node execution
- **Events detected**: Tool calls (sub-agent delegation), tool results, HITL interrupts
- **No fake heartbeats**: All status updates are real agent events

### Other Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cv/upload` | POST | Upload PDF CV, extract profile |
| `/profile` | GET | Get user profile |
| `/preferences` | GET/PUT | Get or update search preferences |
| `/search` | POST | Start background job search |
| `/search/results` | GET | Poll search results |
| `/health` | GET | Health check |

---

## Database Schema

### Application Tables (SQLAlchemy)
- `users` — User accounts
- `profiles` — CV-extracted profile data (skills, experience, titles)
- `preferences` — Job search preferences
- `search_sessions` — Background search sessions
- `job_results` — Search results
- `chat_sessions` — Chat sessions (with `thread_id` for agent state)
- `chat_messages` — Individual messages (with `message_type` and `extra_data`)

### Checkpoint Tables (LangGraph)
Created automatically by `PostgresSaver.setup()`:
- `checkpoints` — Graph state snapshots
- `checkpoint_blobs` — Serialized state data
- `checkpoint_writes` — Pending writes

---

## Frontend

### Stack
- React 19 + Vite 7 + Tailwind CSS 4
- SSE streaming for real-time responses

### HITL UI
- `ChatMessage.jsx` renders confirmation buttons when `message_type === "confirmation"`
- "Approve Search" (accent color) and "Cancel" (border) buttons
- On click → `api.confirmAction(sessionId, approved, ...)` → SSE stream
- After action, buttons are replaced with status text

### Onboarding UI
- Welcome message uses `message_type: "onboarding"` (not `text`)
- `ChatMessage.jsx` renders two action buttons:
  - "Yes, upload my CV" (accent color, upload icon) → triggers file input
  - "No, I'll describe my skills" (outline, edit icon) → sends prompt message
- Buttons disappear after user choice (message type changed to `text`)

### Message Types
| Type | Purpose |
|------|---------|
| `text` | Plain text message |
| `onboarding` | Welcome with action buttons |
| `profile` | Extracted CV profile card |
| `job_selection` | Phase 1 jobs with checkboxes |
| `jobs` | Phase 2 enriched job details |
| `confirmation` | HITL approval buttons |
