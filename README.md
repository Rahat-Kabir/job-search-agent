# Job Search Agent

AI-powered job search agent built on **LangChain DeepAgent** architecture. Uses an orchestrator agent with specialized sub-agents for CV parsing and job searching, powered by **DeepSeek-V3** for cost-effective LLM inference.

**Key Features:**
- Extracts skills from CVs (explicit + inferred)
- Searches multiple sources (Tavily, Brave, Firecrawl)
- Ranks jobs by match score
- Leverages DeepAgent's middleware, AgentHarness, and file system capabilities

## Setup

```bash
# Install dependencies
uv sync

# Copy environment file and add your API keys
cp .env.example .env

# Start PostgreSQL (optional, for persistence)
docker compose up -d
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

## API Server (Optional)

```bash
uv run uvicorn backend.api:app --reload --host 127.0.0.1 --port 8020
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cv/upload` | POST | Upload PDF CV, returns extracted profile |
| `/profile` | GET | Get current user profile |
| `/preferences` | PUT | Update search preferences |
| `/search` | POST | Start job search |
| `/search/results` | GET | Get search results |

All endpoints (except upload) require `X-User-ID` header.

## Architecture

```
Orchestrator Agent (DeepSeek-V3)
├── CV Parser Sub-agent
│   └── Extracts skills (explicit + inferred)
└── Job Searcher Sub-agent
    └── Searches via Tavily, Brave, Firecrawl
```

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

**[LangChain DeepAgent](https://python.langchain.com/docs/concepts/deep_agents/)** - Provides:
- **Middleware** - Request/response processing pipeline
- **Sub-agents** - Specialized agents for CV parsing and job searching
- **AgentHarness** - Orchestration and lifecycle management
- **File system** - Document handling and state persistence

**[DeepSeek-V3](https://www.deepseek.com/)** - Cost-effective LLM choice:
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
