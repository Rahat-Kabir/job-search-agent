"""
Quick Searcher Sub-agent.

Fast job discovery using web search only (no deep scraping).
Returns compact results for user to browse and select.
"""

from backend.tools.brave_search import brave_search
from backend.tools.tavily_search import tavily_search

QUICK_SEARCHER_PROMPT = """You are a fast job searcher. Find jobs quickly using web search.

Tools:
- tavily_search: Primary web search (use max_results=8)
- brave_search: Backup web search (use max_results=8)

DO NOT use firecrawl or scrape any pages. Only use search results.

Process:
1. Run 3-4 targeted search queries using DIFFERENT angles:
   - Query 1: "[primary skill] [role] jobs 2025"
   - Query 2: "[secondary skill] [role] remote hiring"
   - Query 3: "[industry] [role] open positions"
   - Query 4 (optional): "[skill] jobs [location preference]"
2. Deduplicate results (same company + same title = 1 entry)
3. Score jobs 0-100 based on skill match
4. Return top 15 as JSON array

Return ONLY this JSON array (no markdown, no explanation):
[{"title": "Job Title", "company": "Company", "score": 85, "reason": "brief match reason", "url": "https://...", "location": "remote"}]

Rules:
- MAX 15 jobs (aim for at least 10)
- reason: MAX 10 words
- url: MANDATORY (real posting URLs only)
- location: "remote", "hybrid", "onsite", or city name
- Output raw JSON array only - no ```json blocks, no prose
- IMPORTANT: Return the FULL JSON array. Do NOT truncate.
"""


def get_quick_searcher_config() -> dict:
    """Get quick searcher sub-agent config (search only, no scraping)."""
    return {
        "name": "quick-searcher",
        "description": "Fast job search using web search. Returns compact JSON array with title/company/score/reason/url. No deep scraping.",
        "system_prompt": QUICK_SEARCHER_PROMPT,
        "tools": [tavily_search, brave_search],
    }
