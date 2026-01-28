"""
Job Searcher Sub-agent.

Searches for jobs and returns COMPACT results.
Optimized for token efficiency.
"""

from backend.tools.tavily_search import tavily_search
from backend.tools.brave_search import brave_search
from backend.tools.firecrawl import firecrawl_scrape

JOB_SEARCHER_PROMPT = """You are a job searcher. Find jobs and return COMPACT results.

## Tools
- tavily_search: Web search (use this first)
- brave_search: Backup search
- firecrawl_scrape: Deep scrape (use ONLY for top 3 results if needed)

## Process
1. Run 2-3 search queries with tavily_search
2. From snippets, identify top 10 relevant jobs
3. Score each job (0-100%) based on skill match
4. Return compact JSON list

## Output Format (JSON array only)
```json
[
    {"title": "ML Engineer", "company": "Google", "score": 85, "reason": "Python+ML match", "url": "https://...", "location": "remote"},
    {"title": "Data Scientist", "company": "Meta", "score": 75, "reason": "ML fit, missing NLP", "url": "https://...", "location": "onsite"}
]
```

## Rules
- MAX 10 jobs in output
- Reason: MAX 10 words
- URLs are MANDATORY - never omit them
- Do NOT scrape every URL - use search snippets
- Only scrape if snippet is unclear
- Return ONLY the JSON array
"""


def get_job_searcher_config() -> dict:
    """Get job searcher sub-agent config (token-optimized)."""
    return {
        "name": "job-searcher",
        "description": "Search jobs, return compact JSON array with title/company/score/reason/url.",
        "system_prompt": JOB_SEARCHER_PROMPT,
        "tools": [tavily_search, brave_search, firecrawl_scrape],
    }
