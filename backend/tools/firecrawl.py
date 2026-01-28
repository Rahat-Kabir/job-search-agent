"""
Firecrawl tool for job page scraping.

Scrapes full job posting content from URLs.
"""

import httpx
from langchain_core.tools import tool
from markdownify import markdownify

from backend.config import settings

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1/scrape"


@tool
def firecrawl_scrape(url: str) -> str:
    """
    Scrape full content from a job posting URL.

    Args:
        url: URL of the job posting to scrape

    Returns:
        Job posting content as markdown text
    """
    # Try Firecrawl API first, fallback to direct fetch
    if settings.firecrawl_api_key:
        return _scrape_with_firecrawl(url)
    return _scrape_direct(url)


def _scrape_with_firecrawl(url: str) -> str:
    """Scrape using Firecrawl API."""
    try:
        headers = {
            "Authorization": f"Bearer {settings.firecrawl_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "url": url,
            "formats": ["markdown"],
        }

        with httpx.Client(timeout=settings.search_timeout) as client:
            response = client.post(FIRECRAWL_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = data.get("data", {}).get("markdown", "")
        if content:
            return content

        return f"No content extracted from: {url}"

    except httpx.HTTPStatusError as e:
        return f"Firecrawl HTTP error: {e.response.status_code}"
    except Exception as e:
        return f"Firecrawl error: {str(e)}"


def _scrape_direct(url: str) -> str:
    """Fallback: scrape directly with httpx."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        with httpx.Client(timeout=settings.search_timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

        # Convert HTML to markdown
        markdown = markdownify(response.text)

        # Truncate if too long
        if len(markdown) > 10000:
            markdown = markdown[:10000] + "\n\n[Content truncated...]"

        return markdown

    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code}: Could not fetch {url}"
    except Exception as e:
        return f"Scrape error: {str(e)}"
