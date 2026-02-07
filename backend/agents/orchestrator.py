"""
Orchestrator Agent.

Main agent coordinating CV parsing and job search.
Optimized for minimal token usage.
"""

from datetime import datetime
from typing import Any

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.backends.composite import CompositeBackend
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic import BaseModel, Field

from backend.agents.checkpointer import get_checkpointer
from backend.agents.cv_parser import get_cv_parser_config
from backend.agents.detail_scraper import get_detail_scraper_config
from backend.agents.quick_searcher import get_quick_searcher_config
from backend.config import settings

# Path to agent memory file (loaded into system prompt)
AGENTS_MD = str(Path(__file__).resolve().parent / "AGENTS.md")


class AgentState(BaseModel):
    """State for the orchestrator agent."""

    profile: dict[str, Any] | None = None
    jobs: list[dict[str, Any]] = Field(default_factory=list)
    preferences: dict[str, Any] | None = None


CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")

ORCHESTRATOR_PROMPT = f"""You are a friendly job search assistant. Date: {CURRENT_DATE}

## Your Capabilities
1. Parse CVs and extract skills/experience
2. Search for jobs matching user profile (two-phase: quick search + detail scrape)
3. Answer questions about job searching, career advice, skills

## Intent Detection
Detect user intent and respond appropriately:
- CV_UPLOAD: User shares CV text → delegate to cv-parser
- SEARCH_JOBS: User wants job search → delegate to quick-searcher (Phase 1)
- GET_DETAILS: User selected specific jobs for details → delegate to detail-scraper (Phase 2)
- CHAT: General questions → answer directly (no delegation)
- REFINE: User wants to modify search (e.g., "remote only") → update preferences and search

## Sub-agents
- cv-parser: Extract profile → returns JSON {{skills, experience_years, titles, summary}}
- quick-searcher: Fast job search → returns JSON array [{{title, company, score, reason, url, location}}]
- detail-scraper: Deep scrape selected URLs → returns JSON array [{{url, salary, description, requirements, benefits}}]

## Two-Phase Job Search Flow
**Phase 1 - Quick Search:**
1. Delegate to quick-searcher with user profile
2. Present ALL returned jobs to user as a browsable list
3. Tell user: "Select the jobs you'd like more details on, then click 'Get Details'"

**Phase 2 - Detail Scrape (when user provides selected job URLs):**
1. Delegate to detail-scraper with the selected URLs
2. Present enriched job details (salary, description, requirements, benefits)

## Context Trimming (CRITICAL)
When delegating to sub-agents, send ONLY minimal data:
- To cv-parser: Only the CV text
- To quick-searcher: "Find jobs for: Skills: [list], Experience: X years, Roles: [list]"
- To detail-scraper: "Get details for these URLs: [url1, url2, ...]"

## Filesystem Usage
- After a job search completes, save results to /workspace/searches/ for future reference
- After detail scraping, save enriched details to /workspace/details/
- Use /memories/ to store user preferences and profile summaries across sessions
- Use write_file tool to persist data

## Response Style
- Be conversational and helpful
- Keep responses concise (2-3 sentences max for chat)
- When showing jobs, present them clearly as JSON
- Ask clarifying questions if user intent is unclear
"""


def truncate_cv(cv_text: str, max_chars: int = 4000) -> str:
    """
    Truncate CV to essential sections for token efficiency.

    Keeps: Skills, Experience, Education sections
    Removes: Full job descriptions, references, declarations
    """
    if len(cv_text) <= max_chars:
        return cv_text

    # Try to find key sections
    lines = cv_text.split('\n')
    essential_lines = []
    in_section = False
    skip_sections = ['reference', 'declaration', 'certif']

    for line in lines:
        line_lower = line.lower().strip()

        # Skip certain sections
        if any(skip in line_lower for skip in skip_sections):
            in_section = False
            continue

        # Keep lines from important sections
        if any(kw in line_lower for kw in ['skill', 'experience', 'education', 'objective', 'summary', 'project']):
            in_section = True

        if in_section or len(essential_lines) < 50:
            essential_lines.append(line)

        if len('\n'.join(essential_lines)) > max_chars:
            break

    result = '\n'.join(essential_lines)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n[truncated]"

    return result


SEARCH_TOOL_INTERRUPT = {
    "tavily_search": {
        "allowed_decisions": ["approve", "reject"],
        "description": "Job search will call external APIs (Tavily). Approve to proceed.",
    },
    "brave_search": {
        "allowed_decisions": ["approve", "reject"],
        "description": "Backup search will call Brave API. Approve to proceed.",
    },
    "firecrawl_scrape": {
        "allowed_decisions": ["approve", "reject"],
        "description": "Deep scraping selected job postings. Approve to proceed.",
    },
}


def create_orchestrator(
    checkpointer: BaseCheckpointSaver | AsyncPostgresSaver | None = None,
    interrupt_on: dict | None = None,
):
    """Create the orchestrator agent."""
    if not settings.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY not set")

    model = ChatDeepSeek(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        temperature=0.1,
    )

    subagents = [
        get_cv_parser_config(),
        get_quick_searcher_config(),
        get_detail_scraper_config(),
    ]

    # CompositeBackend: route different paths to different storage
    agent_data_dir = str(Path(__file__).resolve().parent.parent.parent / ".agent_data")
    backend = CompositeBackend(
        default=FilesystemBackend(root_dir=agent_data_dir),  # Default ephemeral scratch
        routes={
            "/memories/": FilesystemBackend(root_dir=agent_data_dir + "/memories"),   # Cross-session memories
            "/workspace/": FilesystemBackend(root_dir=agent_data_dir + "/workspace"),  # Persistent search results
        },
    )

    agent_kwargs = {
        "model": model,
        "tools": [],
        "system_prompt": ORCHESTRATOR_PROMPT,
        "subagents": subagents,
        "backend": backend,         # Used by built-in SummarizationMiddleware + FilesystemMiddleware
        "memory": [AGENTS_MD],      # Persistent agent memory loaded into system prompt
    }

    if checkpointer:
        agent_kwargs["checkpointer"] = checkpointer

    if interrupt_on:
        agent_kwargs["interrupt_on"] = interrupt_on

    return create_deep_agent(**agent_kwargs)


def create_orchestrator_with_hitl():
    """Create orchestrator with persistent PostgreSQL checkpointer and HITL."""
    checkpointer = get_checkpointer()
    agent = create_orchestrator(
        checkpointer=checkpointer,
        interrupt_on=SEARCH_TOOL_INTERRUPT,
    )
    return agent, checkpointer
