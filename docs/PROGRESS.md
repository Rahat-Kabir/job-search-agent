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

## Phase 3: Frontend UI
| Task | Status |
|------|--------|
| React + Vite setup | Done |
| Tailwind CSS (Apple-like design) | Done |
| Header + dark mode toggle | Done |
| CV Upload component | Done |
| Profile & Preferences component | Done |
| Search button + loading states | Done |
| Job cards grid | Done |
| API integration | Done |
| FastAPI static file serving | Done |

---

## Phase 4: Optimizations
| Task | Status |
|------|--------|
| CV Truncation (max 4000 chars) | Done |
| Compact prompts (JSON-only output) | Done |
| Selective scraping (top 3 only) | Done |
| State persistence (checkpointer + thread_id) | Done |
| Robust JSON parser with fallback | Done |
| Context trimming in orchestrator | Done |
| Progress status updates | Done |

---

## Optimizations Details

### Robust Parser (`backend/utils/parser.py`)
- Multiple JSON extraction strategies (clean, fenced, bracket-matching)
- Markdown fallback for non-JSON responses
- Handles various AI output formats

### Context Trimming
- Orchestrator sends only compact profile to sub-agents
- Sub-agent prompts enforce raw JSON output (no markdown blocks)
- Max 500 words to sub-agents

### Progress Status Updates
Search statuses: `pending` → `analyzing_profile` → `searching_jobs` → `ranking_results` → `completed`

---

## Phase 5: Conversational Chat Interface
| Task | Status |
|------|--------|
| ChatSession + ChatMessage DB models | Done |
| Chat API endpoint (POST /chat) | Done |
| CV upload via chat (POST /chat/upload) | Done |
| Orchestrator conversational mode | Done |
| Chat UI component | Done |
| Message bubbles (user/assistant) | Done |
| Job cards in chat | Done |
| Profile display in chat | Done |

---

### Chat Architecture
```
User Message → /chat endpoint → Orchestrator (intent detection)
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                 ↓                 ↓
              CV Upload          Job Search         Chat/Q&A
              (cv-parser)      (job-searcher)     (direct response)
```

### API Endpoints
- `POST /chat` - Send message, get response
- `POST /chat/upload` - Upload CV in chat context
- `GET /chat/{session_id}` - Get chat history

---

## Phase 6: Security Hardening
| Task | Status |
|------|--------|
| CORS restricted to frontend domain | Done |
| Rate limiting with slowapi + Redis | Done |
| File size limit on uploads (5 MB) | Done |

---

### Security Details

#### CORS (`backend/api/app.py`)
- Origins restricted via `CORS_ORIGINS` env var (default: `http://localhost:5173`)
- Methods limited to `GET`, `POST`, `PUT`, `DELETE`
- Headers limited to `Content-Type`, `Authorization`

#### Rate Limiting (`backend/api/limiter.py`)
- Backend: Redis (`redis://localhost:6379`)
- `POST /chat` — 5 requests/minute per IP
- `POST /chat/upload` — 3 requests/minute per IP
- `POST /cv/upload` — 3 requests/minute per IP
- `POST /search` — 3 requests/minute per IP
- Exceeding limit returns `429 Too Many Requests`

#### File Size Limit
- Max upload size: 5 MB
- Applied to `/cv/upload` and `/chat/upload`
- Exceeding limit returns `413 Request Entity Too Large`

---

## Phase 7: UI Redesign (Bold & Vibrant → Apple Calm)
| Task | Status |
|------|--------|
| Sidebar with chat history | Done |
| Enhanced JobCard with score ring, bookmark, Apply CTA | Done |
| Message slide-in animations | Done |
| Typing indicator with bouncing dots | Done |
| Drag-and-drop CV upload in ChatInput | Done |
| Removed legacy components (CVUpload, Profile, SearchButton, JobResults, Header) | Done |

### Phase 7b: Apple-like Calm Redesign
| Task | Status |
|------|--------|
| Replace gradient palette with Apple Indigo flat colors | Done |
| Light theme: white (#FFFFFF) + warm gray (#F5F5F7) | Done |
| Dark theme: true black (#000000) + dark gray (#1C1C1E) | Done |
| Remove all gradient backgrounds (buttons, bubbles, logo) | Done |
| Remove ambient gradient blobs | Done |
| Remove gradient-text and gradient-border CSS classes | Done |
| Flat indigo accent on buttons, send, apply CTA | Done |
| Soften card shadows and border-radius | Done |

---

### Redesign Details

#### Design Direction: "Apple Calm"
- **Palette**: Indigo (#5856D6 light / #7D7AFF dark) flat accent — no gradients
- **Typography**: Outfit (display/headings), DM Sans (body text)
- **Dark theme**: True black (#000000) with neutral grays (#1C1C1E, #38383A)
- **Light theme**: Pure white (#FFFFFF) with warm gray (#F5F5F7)
- **Shadows**: Minimal (0 1px 2px), no colored glow shadows
- **Border-radius**: 0.75rem (cards), 0.75rem (buttons)

#### Components
- **Sidebar** (`Sidebar.jsx`): Persistent left panel with session history, flat indigo "New Chat" button, relative timestamps, delete per session, collapsible on mobile
- **ScoreRing** (in `JobCard.jsx`): SVG circular progress with animated fill, color-coded (green ≥80, amber ≥60, gray <60)

#### Removed Components
- `CVUpload.jsx` — replaced by inline ChatInput upload
- `Profile.jsx` — replaced by inline chat profile display
- `SearchButton.jsx` — replaced by chat-driven search
- `JobResults.jsx` — replaced by inline chat job cards
- `Header.jsx` — integrated directly into Chat.jsx

---

## Phase 8: Persistent Checkpointer & HITL

| Task | Status |
|------|--------|
| Add `langgraph-checkpoint-postgres` dependency | Done |
| Create `backend/agents/checkpointer.py` (PostgresSaver lifecycle) | Done |
| Swap `MemorySaver` → `PostgresSaver` in orchestrator | Done |
| Add `interrupt_on` for search tools (HITL) | Done |
| FastAPI lifespan: init/close checkpointer | Done |
| `POST /chat/confirm` endpoint (approve/reject) | Done |
| SSE `confirmation` event for HITL | Done |
| Auto-approve HITL in background search route | Done |
| Frontend: confirmation buttons in ChatMessage | Done |
| Frontend: `confirmAction()` API + SSE handler | Done |
| CLI: HITL prompt (approve/reject) in main.py | Done |
| CLI test script: `scripts/test_hitl.py` | Done |

---

### Phase 8 Architecture

#### Persistent Checkpointer
- **Before**: `MemorySaver` (in-memory, lost on restart)
- **After**: `PostgresSaver` from `langgraph-checkpoint-postgres`
- Uses existing PostgreSQL database (same `DATABASE_URL`)
- Managed via `backend/agents/checkpointer.py` singleton
- Initialized in FastAPI lifespan, closed on shutdown
- Checkpoint tables created automatically via `checkpointer.setup()`

#### HITL (Human-in-the-Loop)
- **Trigger**: Search tools (`tavily_search`, `brave_search`, `firecrawl_scrape`)
- **Mechanism**: DeepAgents `interrupt_on` → LangGraph `interrupt()` → `HumanInTheLoopMiddleware`
- **Decisions**: `approve` or `reject` only (no edit)

#### HITL Flow (Chat UI)
```
User: "Find jobs for me"
  → Agent detects SEARCH_JOBS intent
  → Delegates to job-searcher sub-agent
  → Sub-agent tries to call tavily_search
  → INTERRUPT fires → SSE "confirmation" event
  → Frontend shows Approve/Cancel buttons
  → User clicks Approve
  → POST /chat/confirm {session_id, approved: true}
  → Agent resumes with Command(resume=True)
  → Auto-approves subsequent tool calls in same search
  → Returns job results
```

#### HITL Flow (CLI)
```
You: find me python jobs
[HITL] Agent wants to call external search APIs.
[HITL] Approve? (y/n): y
[HITL] Auto-approving follow-up tool call...
Agent: [job results]
```

#### HITL Flow (Background Search)
- `POST /search` auto-approves all interrupts (user already initiated explicitly)

#### API Changes
- `POST /chat/confirm` — New endpoint for HITL confirmation (SSE streaming)
- `POST /chat/stream` — Now emits `confirmation` SSE event when interrupt fires
- SSE events: `status`, `confirmation`, `done`, `error`

---

## Phase 9: Enhanced Job Search (15 Jobs + Two-Phase Architecture)

| Task | Status |
|------|--------|
| Bump job limit from 10 to 15 | Done |
| Add `SummarizationMiddleware` (built-in via create_deep_agent) | Done |
| Add `FilesystemBackend` for context persistence | Done |
| Add agent memory (`AGENTS.md`) loaded into system prompt | Done |
| Split job-searcher into quick-searcher + detail-scraper | Done |
| `quick-searcher`: Tavily/Brave only, 15 jobs, no scraping | Done |
| `detail-scraper`: Firecrawl for user-selected jobs only | Done |
| Update orchestrator prompt for two-phase flow | Done |
| `POST /chat/get-details` endpoint (SSE streaming) | Done |
| Frontend: checkbox selection on job cards | Done |
| Frontend: "Get Details" bulk action button | Done |
| Frontend: enriched job card (salary, requirements, benefits) | Done |
| `getJobDetails()` API function in frontend | Done |
| CLI test: `scripts/test_job_search.py` (Phase 1) | Done |
| CLI test: `scripts/test_two_phase.py` (Phase 1+2) | Done |

---

### Phase 9 Architecture

#### Two-Phase Job Search Flow
```
Phase 1 (Quick Search):
  User profile -> quick-searcher (Tavily + Brave)
  -> 15 jobs with title/company/score/url
  -> Frontend shows cards with checkboxes

Phase 2 (Detail Scrape - on demand):
  User selects jobs -> "Get Details" button
  -> POST /chat/get-details {selected_urls}
  -> detail-scraper (Firecrawl) scrapes selected URLs
  -> Returns salary, description, requirements, benefits
  -> Frontend updates cards with enriched details
```

#### New Sub-agents
- `quick-searcher` (`backend/agents/quick_searcher.py`): Uses Tavily + Brave only. 3-4 search queries, dedup, score, return top 15. No scraping.
- `detail-scraper` (`backend/agents/detail_scraper.py`): Uses Firecrawl only. Scrapes user-selected URLs for salary, description, requirements, benefits.

#### DeepAgent Features Used
- `create_deep_agent(backend=FilesystemBackend(...))` — persistent context storage
- `create_deep_agent(memory=[AGENTS_MD])` — agent memory loaded into system prompt
- Built-in `SummarizationMiddleware` — auto-compresses long conversations
- Built-in `TodoListMiddleware` — agent plans multi-step tasks
- `SubAgentMiddleware` — isolated context per sub-agent
- `interrupt_on` — HITL approval for search/scrape tools

#### New API Endpoints
- `POST /chat/get-details` — SSE streaming endpoint for Phase 2 detail scraping
  - Request: `{session_id, selected_urls: [...]}`
  - Auto-approves Firecrawl HITL interrupts (user already selected these jobs)

#### Frontend Changes
- `JobCard.jsx`: Added `selectable`, `selected`, `onSelect` props + checkbox UI + enriched details display
- `ChatMessage.jsx`: New `job_selection` message type with checkbox grid + "Get Details" bulk action
- `Chat.jsx`: Added `handleGetDetails()` handler
- `api.js`: Added `getJobDetails()` SSE streaming function

---

## Phase 10: Real-Time Streaming + CompositeBackend

| Task | Status |
|------|--------|
| CompositeBackend (default + /memories/ + /workspace/) | Done |
| Real-time streaming via `agent.astream()` | Done |
| Replace fake heartbeat SSE with real agent events | Done |
| New SSE event type: `agent_event` (tool_call, tool_result, auto_approve) | Done |
| Frontend: handle `agent_event` as real-time status updates | Done |
| Remove unused sync agent functions | Done |
| CLI test: `scripts/test_streaming.py` | Done |

---

### Phase 10 Architecture

#### CompositeBackend
- **Before**: Single `FilesystemBackend` for everything
- **After**: `CompositeBackend` with three routes:
  - `default` -> `FilesystemBackend(.agent_data/)` — ephemeral scratch space
  - `/memories/` -> `FilesystemBackend(.agent_data/memories/)` — cross-session persistent memories
  - `/workspace/` -> `FilesystemBackend(.agent_data/workspace/)` — persistent search results

#### Real-Time Streaming
- **Before**: `agent.invoke()` in thread pool + fake heartbeat SSE stages ("Analyzing...", "Working on it...")
- **After**: `agent.astream(stream_mode="values")` yielding real agent events
- **Events streamed**:
  - `agent_event.tool_call` — "Delegating to sub-agent...", "Searching with Tavily..."
  - `agent_event.tool_result` — "Processing results..."
  - `agent_event.auto_approve` — "Auto-approving follow-up search..."
- All three SSE endpoints updated: `/chat/stream`, `/chat/confirm`, `/chat/get-details`

#### SSE Events (Updated)
| Event | Description |
|-------|-------------|
| `status` | Initial status: `{stage, message}` |
| `agent_event` | Real-time agent event: `{type, tools?, message}` |
| `confirmation` | HITL interrupt: `{session_id, requires_confirmation, message}` |
| `done` | Final response: `{session_id, user_id, message}` |
| `error` | Error: `{message}` |

#### Removed Code
- `_invoke_agent_sync()` — replaced by inline `astream` in `/chat/stream`
- `_confirm_agent_sync()` — replaced by inline `astream` in `/chat/confirm`
- `_get_details_sync()` — replaced by inline `astream` in `/chat/get-details`
- `asyncio` import — no longer needed (no `run_in_executor`)

---

## Phase 11: Guided Onboarding UX

| Task | Status |
|------|--------|
| Fix parser incorrectly detecting numbered lists as jobs | Done |
| New `onboarding` message type with action buttons | Done |
| "Yes, upload my CV" button triggers file upload | Done |
| "No, I'll describe my skills" button starts skills flow | Done |
| Parser now requires URL or company for valid jobs | Done |

---

### Phase 11 Details

#### Problem Fixed
When user said "hi", agent responded with numbered list of capabilities:
```
1. **CV analysis** - Share your CV...
2. **Job searching** - Find jobs...
3. **Career advice** - Ask questions...
```

The `parse_jobs_response()` markdown fallback incorrectly matched this as jobs (regex: `\n(?:\d+[\.\)]\s+\*\*)`) → showed fake job cards with 0% match score. "Get Details" did nothing because fake jobs had no URLs.

#### Solution
1. **Stricter parser** (`backend/utils/parser.py`): Jobs must have URL or meaningful company name
2. **New onboarding UX** (`frontend/src/components/`):
   - `message_type: "onboarding"` with two action buttons
   - "Yes, upload my CV" → triggers file upload dialog
   - "No, I'll describe my skills" → prompts user to describe skills manually
   - Buttons disappear after user choice

#### Files Changed
- `frontend/src/components/Chat.jsx` — New handlers: `handleOnboardingUpload`, `handleOnboardingDescribe`
- `frontend/src/components/ChatMessage.jsx` — New `renderOnboarding()` with styled buttons
- `backend/utils/parser.py` — Filter: `[j for j in jobs if j.get("url") or (j.get("company") and j["company"] != "Unknown")]`

---

## Phase 12: Session Management (Single Source of Truth)

| Task | Status |
|------|--------|
| `GET /chat/sessions` — list all sessions from DB | Done |
| `DELETE /chat/{session_id}` — delete session + messages + memory cleanup | Done |
| Frontend Sidebar fetches from API (not localStorage) | Done |
| Remove localStorage `chatSessions` tracking from Chat.jsx | Done |
| CLI test: `scripts/test_sessions.py` | Done |

---

### Phase 12 Details

#### Problem Fixed
1. **Delete was frontend-only**: Sidebar delete removed from localStorage but NOT from PostgreSQL — data leak (messages persisted forever).
2. **Dual data storage**: Session list stored in both localStorage (frontend) and PostgreSQL (backend), causing desync across browsers/devices.

#### Solution
- **Backend is now single source of truth** for session listing and deletion.
- `GET /chat/sessions` returns all sessions with title/preview computed from first user message.
- `DELETE /chat/{session_id}` cascading-deletes messages, session, and cleans up in-memory agent (`_agent_sessions`).
- Frontend Sidebar calls `api.listSessions()` on mount/change. `api.deleteSession()` on delete.
- Removed `saveSession()` callback and all `localStorage.setItem('chatSessions', ...)` writes from `Chat.jsx`.
- `localStorage.chatSessionId` kept for remembering active session pointer only.

#### New API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat/sessions` | GET | List all sessions `{id, title, preview, created_at, updated_at}` |
| `/chat/{session_id}` | DELETE | Delete session + messages + agent memory |

#### New Schemas
- `ChatSessionResponse` — `{id, title, preview, created_at, updated_at}`
- `ChatSessionListResponse` — `{sessions: [ChatSessionResponse]}`

#### Files Changed
- `backend/api/schemas.py` — Added `ChatSessionResponse`, `ChatSessionListResponse`
- `backend/api/routes/chat.py` — Added `list_sessions()`, `delete_session()` endpoints
- `frontend/src/api.js` — Added `listSessions()`, `deleteSession()`
- `frontend/src/components/Sidebar.jsx` — Rewritten to fetch from API
- `frontend/src/components/Chat.jsx` — Removed `saveSession` and localStorage session writes

---

## Phase 13: Memory Leak Fix + SSE DB Session Safety

| Task | Status |
|------|--------|
| Replace `_agent_sessions` dict with `TTLCache(maxsize=200, ttl=3600)` | Done |
| SSE `/stream` generator: own DB session with `finally: close()` | Done |
| SSE `/confirm` generator: own DB session with `finally: close()` | Done |
| SSE `/get-details` generator: own DB session with `finally: close()` | Done |
| Add `cachetools` dependency | Done |

---

### Phase 13 Details

#### Memory Leak Fix
- **Before**: `_agent_sessions: dict[str, tuple] = {}` — unbounded, never evicts entries
- **After**: `_agent_sessions: TTLCache = TTLCache(maxsize=200, ttl=3600)` — max 200 agents, auto-evict after 1h
- Evicted agents are recreated on-demand; PostgreSQL checkpointer restores conversation state transparently

#### SSE DB Session Fix
- **Before**: SSE generators used the `db` session from `Depends(get_db)`, which could be closed by FastAPI before the generator finished. Also blocked the async event loop on `db.commit()`.
- **After**: Each generator creates its own `gen_db = next(get_db())` with explicit `finally: gen_db.close()`. This guarantees the session stays alive for the generator's full lifetime and is cleaned up properly.
- Applied to all 3 SSE endpoints: `/chat/stream`, `/chat/confirm`, `/chat/get-details`

#### Files Changed
- `backend/api/routes/chat.py` — TTLCache import, replaced dict, 3 generators refactored
- `pyproject.toml` / `uv.lock` — `cachetools` dependency added

---

## Known Issue
**Token usage** still elevated due to Deep Agents sub-agent architecture.

Mitigation applied:
- Trimmed context passing via prompts
- Compact JSON-only outputs
- Expected reduction: 30-50%
