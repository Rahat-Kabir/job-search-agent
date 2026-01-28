"""FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.base import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    try:
        init_db()
    except ValueError:
        pass  # Database not configured, skip init
    yield


app = FastAPI(
    title="Job Search Agent API",
    description="AI-powered job search using CV analysis",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Import and include routers
from backend.api.routes import cv, preferences, profile, search  # noqa: E402

app.include_router(cv.router, prefix="/cv", tags=["CV"])
app.include_router(profile.router, prefix="/profile", tags=["Profile"])
app.include_router(preferences.router, prefix="/preferences", tags=["Preferences"])
app.include_router(search.router, prefix="/search", tags=["Search"])


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
