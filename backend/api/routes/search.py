"""Search endpoints."""

import json
import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.agents.orchestrator import create_orchestrator_with_hitl
from backend.api.schemas import JobResultResponse, SearchRequest, SearchResultsResponse
from backend.db import JobResult, Preferences, Profile, SearchSession, get_db

router = APIRouter()


def parse_job_results(agent_response: str) -> list[dict]:
    """Extract job results from agent response (handles JSON or markdown)."""
    # Try JSON first
    try:
        if "```json" in agent_response:
            json_str = agent_response.split("```json")[1].split("```")[0]
            results = json.loads(json_str.strip())
            if isinstance(results, list):
                return results
    except (json.JSONDecodeError, IndexError):
        pass

    results = []
    # Split by numbered items: 1. **Title** or 2. **Title**
    job_blocks = re.split(r"\n\d+\.\s+\*\*", agent_response)

    for block in job_blocks[1:]:  # Skip first empty split
        job = {}

        # Format 1: "Title** (Score: 90%)"
        # Format 2: "Title** - Company" with "Score: 90/100" on separate line
        title_line = block.split("\n")[0]

        # Try Format 1: Title** (Score: XX%)
        title_match = re.match(r"([^*]+)\*\*\s*\(Score:\s*(\d+)", title_line)
        if title_match:
            title_text = title_match.group(1).strip()
            if " at " in title_text:
                parts = title_text.rsplit(" at ", 1)
                job["title"] = parts[0].strip()
                job["company"] = parts[1].strip()
            else:
                job["title"] = title_text
            job["score"] = int(title_match.group(2))
        else:
            # Format 2: Title** - Company
            title_match2 = re.match(r"([^*]+)\*\*\s*[-–]\s*(.+)", title_line)
            if title_match2:
                job["title"] = title_match2.group(1).strip()
                job["company"] = title_match2.group(2).strip()

        # Extract score from separate line: - Score: 90/100 or Score: 90%
        score_match = re.search(r"Score:\s*(\d+)", block)
        if score_match and "score" not in job:
            job["score"] = int(score_match.group(1))

        # Extract match reason: - Match: ... or **Match:** ...
        match_match = re.search(r"Match:\s*([^\n]+)", block)
        if match_match:
            job["reason"] = match_match.group(1).strip()

        # Extract reason if labeled differently
        reason_match = re.search(r"Reason:\s*([^\n]+)", block)
        if reason_match and "reason" not in job:
            job["reason"] = reason_match.group(1).strip()

        # Extract URL from markdown link: [text](url) or plain URL
        url_match = re.search(r"\]\((https?://[^\)]+)\)", block)
        if url_match:
            job["url"] = url_match.group(1)
        else:
            url_match2 = re.search(r"(https?://[^\s\)]+)", block)
            if url_match2:
                job["url"] = url_match2.group(1)

        # Extract location
        if re.search(r"\bremote\b", block.lower()):
            job["location"] = "remote"
        elif re.search(r"\bonsite\b", block.lower()):
            job["location"] = "onsite"
        elif re.search(r"\bhybrid\b", block.lower()):
            job["location"] = "hybrid"

        if job.get("title"):
            results.append(job)

    return results


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

        search.status = "running"
        db.commit()

        # Create agent and run search
        logger.info(f"Starting search {search_id}")
        agent, _ = create_orchestrator_with_hitl()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}

        # Send profile, then approve to trigger job search
        # Step 1: Send profile
        messages = [{"role": "user", "content": f"Here's my profile:\n\n{profile_context}"}]
        result = agent.invoke({"messages": messages}, config=config)

        # Step 2: Approve/confirm to trigger actual job search
        messages.append({"role": "user", "content": "approve"})
        result = agent.invoke({"messages": messages}, config=config)

        response_msgs = result.get("messages", [])
        agent_response = getattr(response_msgs[-1], "content", "") if response_msgs else ""

        logger.info(f"Agent response length: {len(agent_response)}")
        logger.info(f"Agent response: {agent_response[:500]}...")

        # Parse and store results
        jobs = parse_job_results(agent_response)
        logger.info(f"Parsed {len(jobs)} jobs")
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

        search.status = "completed"
        search.completed_at = datetime.now(UTC)
        db.commit()

    except Exception as e:
        search = db.query(SearchSession).filter(SearchSession.id == search_id).first()
        if search:
            search.status = "failed"
            db.commit()
        raise e
    finally:
        db.close()


@router.post("")
def start_search(
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
