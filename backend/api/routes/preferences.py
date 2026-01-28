"""Preferences endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.api.schemas import PreferencesResponse, PreferencesUpdate
from backend.db import Preferences, get_db

router = APIRouter()


@router.get("", response_model=PreferencesResponse)
def get_preferences(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    """Get user search preferences."""
    prefs = db.query(Preferences).filter(Preferences.user_id == x_user_id).first()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")

    return PreferencesResponse(
        location_type=prefs.location_type,
        target_roles=prefs.target_roles or [],
        excluded_companies=prefs.excluded_companies or [],
        min_salary=prefs.min_salary,
    )


@router.put("", response_model=PreferencesResponse)
def update_preferences(
    data: PreferencesUpdate,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    """Update user search preferences."""
    prefs = db.query(Preferences).filter(Preferences.user_id == x_user_id).first()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")

    if data.location_type is not None:
        prefs.location_type = data.location_type
    if data.target_roles is not None:
        prefs.target_roles = data.target_roles
    if data.excluded_companies is not None:
        prefs.excluded_companies = data.excluded_companies
    if data.min_salary is not None:
        prefs.min_salary = data.min_salary

    prefs.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(prefs)

    return PreferencesResponse(
        location_type=prefs.location_type,
        target_roles=prefs.target_roles or [],
        excluded_companies=prefs.excluded_companies or [],
        min_salary=prefs.min_salary,
    )
