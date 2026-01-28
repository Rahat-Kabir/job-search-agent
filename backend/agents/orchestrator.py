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

ORCHESTRATOR_PROMPT = f"""You are a job search assistant. Date: {CURRENT_DATE}

## Workflow
1. When user shares CV: delegate to cv-parser, get compact profile
2. Show profile summary, ask user to confirm or add preferences
3. When user approves: delegate to job-searcher with profile + preferences
4. Present job results to user

## Sub-agents
- cv-parser: Returns JSON with skills, experience, titles, summary
- job-searcher: Returns JSON array of jobs with score/reason/url

## Rules
- Be CONCISE - short responses
- Pass ONLY the compact profile to job-searcher (not full CV)
- If user says "approve" or "search", proceed with job search
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
