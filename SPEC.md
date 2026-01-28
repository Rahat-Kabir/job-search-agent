# Job Search Agent - Specification

## Overview
A job search agent that extracts skills from uploaded CVs and finds matching jobs using multiple search APIs. Built with LangChain Deep Agents.

---

## Core Architecture

### Agent Structure
```
Orchestrator Agent (DeepSeek-V3)
├── CV Parser Sub-agent
│   └── Extracts skills (explicit + inferred)
└── Job Searcher Sub-agent
    └── Searches via Tavily, Brave, Firecrawl
```

### Tech Stack
- **Model**: DeepSeek-V3 via `langchain_deepseek.ChatDeepSeek`
- **Framework**: LangChain Deep Agents (`create_deep_agent`)
- **API**: FastAPI
- **Database**: PostgreSQL (Docker) for user profiles + preferences
- **Tracing**: LangSmith

---

## Features

### 1. CV Processing
- **Input**: PDF only
- **Skill extraction**: Explicit + inferred from context
- **Output**: Compact JSON profile (top 10 skills, summary)

### 2. Job Search
- **Search**: Tavily + Brave (parallel)
- **Scraping**: Firecrawl for top 3 results only
- **Location**: Remote vs On-site filter
- **Deduplication**: Title + company match

### 3. Results
- Ranked list with match scores
- Brief match reason per job
- Salary if available
- Quality flag for suspicious postings

### 4. Human-in-the-Loop
- User approves profile before search
- User can modify search preferences

---

## API Design (FastAPI)

```
POST /cv/upload          - Upload PDF, returns profile
GET  /profile            - Get current profile
PUT  /preferences        - Update preferences
POST /search             - Execute search
GET  /search/results     - Get results
```

---

## Data Models

### Profile
```python
{
    "skills": ["Python", "ML", "PyTorch"],
    "experience_years": 2,
    "titles": ["ML Engineer"],
    "summary": "ML researcher..."
}
```

### Job
```python
{
    "title": str,
    "company": str,
    "score": int,  # 0-100
    "reason": str,
    "url": str,
    "location": "remote"|"onsite"
}
```

---

## Environment Variables
```
DEEPSEEK_API_KEY=
TAVILY_API_KEY=
BRAVE_API_KEY=
FIRECRAWL_API_KEY=
LANGSMITH_API_KEY=
DATABASE_URL=postgresql://...
```

---

## Implementation Priority
1. Core agents (CV parser, Job searcher, Orchestrator)
2. FastAPI endpoints
3. PostgreSQL persistence

---

## References
- Deep Agents: https://docs.langchain.com/oss/python/deepagents/overview
- DeepSeek: https://reference.langchain.com/python/integrations/langchain_deepseek/
