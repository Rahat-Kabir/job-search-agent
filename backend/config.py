"""
Configuration management for Job Search Agent.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # LLM
    deepseek_api_key: str = ""

    # Search APIs
    tavily_api_key: str = ""
    brave_api_key: str = ""
    firecrawl_api_key: str = ""

    # Database
    database_url: str = ""

    # Observability
    langsmith_api_key: str = ""
    langsmith_tracing: bool = True

    # Agent settings
    max_search_results: int = 15
    search_timeout: float = 30.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars


settings = Settings()
