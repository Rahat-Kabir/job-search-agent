"""FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.db.base import init_db

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"


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
from backend.api.routes import chat, cv, preferences, profile, search  # noqa: E402

app.include_router(cv.router, prefix="/cv", tags=["CV"])
app.include_router(profile.router, prefix="/profile", tags=["Profile"])
app.include_router(preferences.router, prefix="/preferences", tags=["Preferences"])
app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Serve static files from frontend build
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes."""
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
