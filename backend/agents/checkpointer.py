"""
Persistent checkpointer using PostgreSQL (async version).

Manages AsyncPostgresSaver lifecycle for the application.
Requires DATABASE_URL to be configured.
"""

from __future__ import annotations

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from backend.config import settings

_checkpointer: AsyncPostgresSaver | None = None
_context_manager = None  # stores the async context manager


async def init_checkpointer() -> AsyncPostgresSaver:
    """Initialize the async PostgreSQL checkpointer. Call once at app startup."""
    global _checkpointer, _context_manager
    if _checkpointer is not None:
        return _checkpointer

    if not settings.database_url:
        raise ValueError("DATABASE_URL not configured — cannot create checkpointer")

    # Strip SQLAlchemy driver suffix — AsyncPostgresSaver needs plain postgresql:// URI
    conn_string = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    # Create async context manager and enter it
    _context_manager = AsyncPostgresSaver.from_conn_string(conn_string)
    _checkpointer = await _context_manager.__aenter__()
    await _checkpointer.setup()

    return _checkpointer


def get_checkpointer() -> AsyncPostgresSaver:
    """Get the active checkpointer. Raises if not initialized."""
    if _checkpointer is None:
        raise RuntimeError("Checkpointer not initialized — call init_checkpointer() first")
    return _checkpointer


async def close_checkpointer() -> None:
    """Close the checkpointer connection pool. Call at app shutdown."""
    global _checkpointer, _context_manager
    if _context_manager is not None:
        await _context_manager.__aexit__(None, None, None)
        _context_manager = None
    _checkpointer = None
