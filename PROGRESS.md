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

## Known Issue
**Token usage** still elevated due to Deep Agents sub-agent architecture.

Mitigation applied:
- Trimmed context passing via prompts
- Compact JSON-only outputs
- Expected reduction: 30-50%
