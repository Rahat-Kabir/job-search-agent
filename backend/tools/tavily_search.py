"""
Tavily search tool for job discovery.

Uses Tavily API to search the web for job postings.
"""

from typing import Literal

from langchain_core.tools import tool
from tavily import TavilyClient

from backend.config import settings

# Initialize client (lazy - only when API key is set)
_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    """Get or create Tavily client."""
    global _client
    if _client is None:
        if not settings.tavily_api_key:
            raise ValueError("TAVILY_API_KEY not set")
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client


@tool
def tavily_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news"] = "general",
) -> str:
    """
    Search the web for job postings using Tavily.

    Args:
        query: Search query (e.g., "Python developer remote jobs")
        max_results: Maximum number of results to return
        topic: Search topic filter - 'general' or 'news'

    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    try:
        client = _get_client()
        results = client.search(
            query=query,
            max_results=max_results,
            topic=topic,
        )

        # Format results
        formatted = []
        for r in results.get("results", []):
            formatted.append(
                f"**{r['title']}**\n"
                f"URL: {r['url']}\n"
                f"{r.get('content', 'No description')}\n"
            )

        if not formatted:
            return f"No results found for: {query}"

        return f"Found {len(formatted)} results:\n\n" + "\n---\n".join(formatted)

    except Exception as e:
        return f"Tavily search error: {str(e)}"
