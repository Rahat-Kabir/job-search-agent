"""CV upload endpoint."""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.agents.orchestrator import create_orchestrator_with_hitl, truncate_cv
from backend.api.schemas import CVUploadResponse, ProfileResponse, SkillResponse
from backend.db import Profile, Preferences, User, get_db
from backend.tools.pdf_parser import parse_pdf as parse_pdf_tool
from backend.utils.parser import parse_profile_response

router = APIRouter()


@router.post("/upload", response_model=CVUploadResponse)
async def upload_cv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a CV (PDF) and extract profile."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Parse PDF
    content = await file.read()
    try:
        cv_text = parse_pdf_tool.invoke({"pdf_content": content})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {e}")

    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="PDF appears to be empty or unreadable")

    # Truncate for token efficiency
    cv_text = truncate_cv(cv_text, max_chars=4000)

    # Create agent and extract profile
    try:
        agent, _ = create_orchestrator_with_hitl()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}

        result = agent.invoke(
            {"messages": [{"role": "user", "content": f"Here's my CV:\n\n{cv_text}"}]},
            config=config,
        )

        response_msgs = result.get("messages", [])
        agent_response = getattr(response_msgs[-1], "content", "") if response_msgs else ""
        profile_data = parse_profile_response(agent_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")

    # Create user and profile in database
    user = User(id=str(uuid.uuid4()))
    db.add(user)

    # Convert skills to list of dicts for JSON storage
    skills_json = [
        {"name": s, "confidence": 1.0, "source": "explicit"}
        for s in profile_data.get("skills", [])
    ]

    profile = Profile(
        user_id=user.id,
        skills=skills_json,
        experience_years=profile_data.get("experience_years"),
        job_titles=profile_data.get("titles", []),
        summary=profile_data.get("summary", ""),
        cv_text=cv_text,
    )
    db.add(profile)

    # Create default preferences
    preferences = Preferences(user_id=user.id)
    db.add(preferences)

    db.commit()
    db.refresh(profile)

    return CVUploadResponse(
        user_id=user.id,
        profile=ProfileResponse(
            skills=[SkillResponse(**s) for s in skills_json],
            experience_years=profile.experience_years,
            job_titles=profile.job_titles,
            summary=profile.summary,
            uploaded_at=profile.uploaded_at,
        ),
        message="Profile extracted successfully",
    )
