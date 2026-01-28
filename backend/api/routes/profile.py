"""Profile endpoint."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.api.schemas import ProfileResponse, SkillResponse
from backend.db import Profile, get_db

router = APIRouter()


@router.get("", response_model=ProfileResponse)
def get_profile(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    """Get user profile."""
    profile = db.query(Profile).filter(Profile.user_id == x_user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ProfileResponse(
        skills=[SkillResponse(**s) for s in (profile.skills or [])],
        experience_years=profile.experience_years,
        job_titles=profile.job_titles or [],
        summary=profile.summary or "",
        uploaded_at=profile.uploaded_at,
    )
