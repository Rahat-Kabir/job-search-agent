"""
Brave search tool for job discovery.

Uses Brave Search API to find job postings.
"""

import httpx
from langchain_core.tools import tool

from backend.config import settings

BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"


@tool
def brave_search(
    query: str,
    max_results: int = 5,
) -> str:
    """
    Search the web for job postings using Brave Search.

    Args:
        query: Search query (e.g., "React developer jobs NYC")
        max_results: Maximum number of results to return

    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    if not settings.brave_api_key:
        return "Brave search unavailable: BRAVE_API_KEY not set"

    try:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": settings.brave_api_key,
        }
        params = {
            "q": query,
            "count": max_results,
        }

        with httpx.Client(timeout=settings.search_timeout) as client:
            response = client.get(BRAVE_API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        # Format results
        formatted = []
        web_results = data.get("web", {}).get("results", [])

        for r in web_results:
            formatted.append(
                f"**{r.get('title', 'No title')}**\n"
                f"URL: {r.get('url', '')}\n"
                f"{r.get('description', 'No description')}\n"
            )

        if not formatted:
            return f"No results found for: {query}"

        return f"Found {len(formatted)} results:\n\n" + "\n---\n".join(formatted)

    except httpx.HTTPStatusError as e:
        return f"Brave search HTTP error: {e.response.status_code}"
    except Exception as e:
        return f"Brave search error: {str(e)}"
