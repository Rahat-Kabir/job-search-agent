"""
Job Searcher Sub-agent.

Searches for jobs and returns COMPACT results.
Optimized for token efficiency.
"""

from backend.tools.tavily_search import tavily_search
from backend.tools.brave_search import brave_search
from backend.tools.firecrawl import firecrawl_scrape

JOB_SEARCHER_PROMPT = """You are a job searcher. Find and rank jobs.

Tools:
- tavily_search: Primary web search
- brave_search: Backup search
- firecrawl_scrape: Deep scrape (top 3 only, if snippet unclear)

Process:
1. Run 2-3 targeted search queries
2. Score jobs 0-100 based on skill match
3. Return top 10 as JSON array

Return ONLY this JSON array (no markdown, no explanation):
[{"title": "Job Title", "company": "Company", "score": 85, "reason": "brief match reason", "url": "https://...", "location": "remote"}]

Rules:
- MAX 10 jobs
- reason: MAX 10 words
- url: MANDATORY (real posting URLs only)
- location: "remote", "hybrid", "onsite", or city name
- Output raw JSON array only - no ```json blocks, no prose
"""


def get_job_searcher_config() -> dict:
    """Get job searcher sub-agent config (token-optimized)."""
    return {
        "name": "job-searcher",
        "description": "Search jobs, return compact JSON array with title/company/score/reason/url.",
        "system_prompt": JOB_SEARCHER_PROMPT,
        "tools": [tavily_search, brave_search, firecrawl_scrape],
    }
