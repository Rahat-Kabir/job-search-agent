"""Search endpoints."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from langgraph.types import Command
from sqlalchemy.orm import Session

from backend.agents.orchestrator import create_orchestrator_with_hitl
from backend.api.limiter import limiter
from backend.api.schemas import JobResultResponse, SearchRequest, SearchResultsResponse
from backend.db import JobResult, Preferences, Profile, SearchSession, get_db
from backend.utils.parser import parse_jobs_response

router = APIRouter()


def _update_status(db, search_id: str, status: str):
    """Helper to update search status."""
    search = db.query(SearchSession).filter(SearchSession.id == search_id).first()
    if search:
        search.status = status
        db.commit()


def run_search(search_id: str, profile_context: str, db_url: str):
    """Background task to run job search."""
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        search = db.query(SearchSession).filter(SearchSession.id == search_id).first()
        if not search:
            return

        # Status: Analyzing profile
        _update_status(db, search_id, "analyzing_profile")
        logger.info(f"[{search_id}] Analyzing profile...")

        agent, _ = create_orchestrator_with_hitl()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}

        # Step 1: Send compact profile (context already trimmed by caller)
        messages = [{"role": "user", "content": f"Find jobs for:\n{profile_context}"}]
        result = agent.invoke({"messages": messages}, config=config)

        # Auto-approve any HITL interrupts (user already initiated search explicitly)
        while "__interrupt__" in result and len(result["__interrupt__"]) > 0:
            logger.info(f"[{search_id}] Auto-approving HITL interrupt...")
            result = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config)

        # Status: Searching jobs
        _update_status(db, search_id, "searching_jobs")
        logger.info(f"[{search_id}] Searching jobs...")

        # Step 2: Approve to trigger job search
        messages.append({"role": "user", "content": "approve"})
        result = agent.invoke({"messages": messages}, config=config)

        # Auto-approve any remaining HITL interrupts
        while "__interrupt__" in result and len(result["__interrupt__"]) > 0:
            logger.info(f"[{search_id}] Auto-approving HITL interrupt...")
            result = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config)

        # Status: Ranking results
        _update_status(db, search_id, "ranking_results")
        logger.info(f"[{search_id}] Ranking results...")

        response_msgs = result.get("messages", [])
        agent_response = getattr(response_msgs[-1], "content", "") if response_msgs else ""

        logger.info(f"Agent response length: {len(agent_response)}")
        logger.info(f"Agent response preview: {agent_response[:500]}...")

        # Parse and store results
        jobs = parse_jobs_response(agent_response)
        logger.info(f"[{search_id}] Parsed {len(jobs)} jobs")

        for job in jobs:
            job_result = JobResult(
                search_id=search_id,
                title=job.get("title", "Unknown"),
                company=job.get("company", "Unknown"),
                match_score=float(job.get("score", 0)) / 100.0,
                match_reason=job.get("reason", ""),
                location_type=job.get("location", "unknown"),
                posting_url=job.get("url", ""),
            )
            db.add(job_result)

        # Status: Completed
        search = db.query(SearchSession).filter(SearchSession.id == search_id).first()
        if search:
            search.status = "completed"
            search.completed_at = datetime.now(UTC)
            db.commit()

        logger.info(f"[{search_id}] Search completed with {len(jobs)} results")

    except Exception as e:
        logger.error(f"[{search_id}] Search failed: {e}")
        _update_status(db, search_id, "failed")
        raise e
    finally:
        db.close()


@router.post("")
@limiter.limit("3/minute")
def start_search(
    request: Request,
    background_tasks: BackgroundTasks,
    data: SearchRequest | None = None,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    """Start a job search."""
    profile = db.query(Profile).filter(Profile.user_id == x_user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Upload CV first.")

    prefs = db.query(Preferences).filter(Preferences.user_id == x_user_id).first()

    # Build profile context for agent
    skills_str = ", ".join(s.get("name", "") for s in (profile.skills or []))
    titles_str = ", ".join(profile.job_titles or [])

    profile_context = f"""Skills: {skills_str}
Experience: {profile.experience_years or 'Unknown'} years
Recent Roles: {titles_str}
Summary: {profile.summary}"""

    if prefs:
        profile_context += f"""
Location preference: {prefs.location_type}
Target roles: {', '.join(prefs.target_roles or [])}"""

    # Create search session
    search = SearchSession(
        user_id=x_user_id,
        queries=data.queries if data and data.queries else [],
    )
    db.add(search)
    db.commit()
    db.refresh(search)

    # Get database URL for background task
    from backend.config import settings

    # Run search in background
    background_tasks.add_task(run_search, search.id, profile_context, settings.database_url)

    return {"search_id": search.id, "status": "pending", "message": "Search started"}


@router.get("/results", response_model=SearchResultsResponse)
def get_search_results(
    search_id: str,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    """Get search results."""
    search = (
        db.query(SearchSession)
        .filter(SearchSession.id == search_id, SearchSession.user_id == x_user_id)
        .first()
    )
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    results = db.query(JobResult).filter(JobResult.search_id == search_id).all()

    return SearchResultsResponse(
        search_id=search.id,
        status=search.status,
        results=[
            JobResultResponse(
                id=r.id,
                title=r.title,
                company=r.company,
                match_score=r.match_score,
                match_reason=r.match_reason,
                location_type=r.location_type,
                salary=r.salary,
                posting_url=r.posting_url,
                description_snippet=r.description_snippet,
            )
            for r in results
        ],
        created_at=search.created_at,
        completed_at=search.completed_at,
    )
