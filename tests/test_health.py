"""Test the FastAPI health endpoint."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Stub out heavy dependencies that aren't needed for health check tests.
# The backend.agents package eagerly imports deepagents/langchain at init,
# which may not be installed in a lightweight test environment.
for mod_name in [
    "deepagents",
    "deepagents.backends",
    "deepagents.backends.composite",
    "langchain_deepseek",
    "langgraph.checkpoint.base",
    "langgraph.checkpoint.postgres",
    "langgraph.checkpoint.postgres.aio",
]:
    sys.modules.setdefault(mod_name, MagicMock())

import backend.agents.checkpointer  # noqa: E402
import backend.db.base  # noqa: E402


def test_health_returns_200():
    with (
        patch.object(backend.db.base, "init_db"),
        patch.object(
            backend.agents.checkpointer,
            "init_checkpointer",
            new_callable=AsyncMock,
        ),
        patch.object(
            backend.agents.checkpointer,
            "close_checkpointer",
            new_callable=AsyncMock,
        ),
    ):
        from fastapi.testclient import TestClient

        from backend.api.app import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}
