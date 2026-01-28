"""
Tools for the Job Search Agent.

- pdf_parser: Extract text from PDF files
- tavily_search: Web search via Tavily API
- brave_search: Web search via Brave API
- firecrawl: Web scraping via Firecrawl API
"""

from backend.tools.pdf_parser import parse_pdf
from backend.tools.tavily_search import tavily_search
from backend.tools.brave_search import brave_search
from backend.tools.firecrawl import firecrawl_scrape

__all__ = ["parse_pdf", "tavily_search", "brave_search", "firecrawl_scrape"]
