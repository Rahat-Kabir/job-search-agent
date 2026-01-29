"""
Orchestrator Agent.

Main agent coordinating CV parsing and job search.
Optimized for minimal token usage.
"""

from datetime import datetime
from typing import Any

from deepagents import create_deep_agent
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from backend.agents.cv_parser import get_cv_parser_config
from backend.agents.job_searcher import get_job_searcher_config
from backend.config import settings


class AgentState(BaseModel):
    """State for the orchestrator agent."""

    profile: dict[str, Any] | None = None
    jobs: list[dict[str, Any]] = Field(default_factory=list)
    preferences: dict[str, Any] | None = None


CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")

ORCHESTRATOR_PROMPT = f"""You are a friendly job search assistant. Date: {CURRENT_DATE}

## Your Capabilities
1. Parse CVs and extract skills/experience
2. Search for jobs matching user profile
3. Answer questions about job searching, career advice, skills

## Intent Detection
Detect user intent and respond appropriately:
- CV_UPLOAD: User shares CV text → delegate to cv-parser
- SEARCH_JOBS: User wants job search → delegate to job-searcher
- CHAT: General questions → answer directly (no delegation)
- REFINE: User wants to modify search (e.g., "remote only") → update preferences and search

## Sub-agents
- cv-parser: Extract profile → returns JSON {{skills, experience_years, titles, summary}}
- job-searcher: Find jobs → returns JSON array [{{title, company, score, reason, url, location}}]

## Conversation Flow
1. Greet user warmly if first message
2. If CV shared: parse it, show summary, ask if ready to search
3. If user describes skills directly (no CV): build profile from description
4. If user says "search/find jobs/yes/ok": delegate to job-searcher
5. If user asks questions: answer helpfully without delegating

## Context Trimming (CRITICAL)
When delegating to sub-agents, send ONLY minimal data:
- To cv-parser: Only the CV text
- To job-searcher: "Find jobs for: Skills: [list], Experience: X years, Roles: [list]"

## Response Style
- Be conversational and helpful
- Keep responses concise (2-3 sentences max for chat)
- When showing jobs, present them clearly
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


def create_orchestrator(checkpointer: MemorySaver | None = None):
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
        get_job_searcher_config(),
    ]

    agent_kwargs = {
        "model": model,
        "tools": [],
        "system_prompt": ORCHESTRATOR_PROMPT,
        "subagents": subagents,
    }

    if checkpointer:
        agent_kwargs["checkpointer"] = checkpointer

    return create_deep_agent(**agent_kwargs)


def create_orchestrator_with_hitl():
    """Create orchestrator with state persistence."""
    checkpointer = MemorySaver()
    agent = create_orchestrator(checkpointer=checkpointer)
    return agent, checkpointer
