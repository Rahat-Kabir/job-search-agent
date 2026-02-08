# ── Stage 1: Build ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies only (skip building the project itself)
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY backend/ backend/
COPY main.py ./

# Now install the project itself
RUN uv sync --frozen --no-dev --no-editable

# ── Stage 2: Runtime ───────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy venv + source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/backend backend/
COPY --from=builder /app/main.py ./

# Use the venv Python
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8020

CMD ["uvicorn", "backend.api.app:app", "--host", "0.0.0.0", "--port", "8020"]
