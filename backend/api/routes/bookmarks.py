"""Bookmark endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.api.schemas import BookmarkCreate, BookmarkListResponse, BookmarkResponse
from backend.db import Bookmark, get_db

router = APIRouter()


@router.post("", response_model=BookmarkResponse)
def create_bookmark(
    bookmark: BookmarkCreate,
    db: Session = Depends(get_db),
):
    """Create a new bookmark."""
    # Check if already bookmarked (same session + url)
    existing = (
        db.query(Bookmark)
        .filter(Bookmark.session_id == bookmark.session_id, Bookmark.posting_url == bookmark.posting_url)
        .first()
    )
    if existing:
        return BookmarkResponse.model_validate(existing)

    db_bookmark = Bookmark(
        session_id=bookmark.session_id,
        title=bookmark.title,
        company=bookmark.company,
        match_score=bookmark.match_score,
        match_reason=bookmark.match_reason,
        location_type=bookmark.location_type,
        salary=bookmark.salary,
        posting_url=bookmark.posting_url,
        description_snippet=bookmark.description_snippet,
    )
    db.add(db_bookmark)
    db.commit()
    db.refresh(db_bookmark)
    return BookmarkResponse.model_validate(db_bookmark)


@router.delete("/{bookmark_id}")
def delete_bookmark(
    bookmark_id: str,
    db: Session = Depends(get_db),
):
    """Delete a bookmark by ID."""
    bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bookmark)
    db.commit()
    return {"message": "Bookmark deleted"}


@router.delete("/url/{session_id}")
def delete_bookmark_by_url(
    session_id: str,
    posting_url: str,
    db: Session = Depends(get_db),
):
    """Delete a bookmark by session_id and posting_url."""
    bookmark = (
        db.query(Bookmark)
        .filter(Bookmark.session_id == session_id, Bookmark.posting_url == posting_url)
        .first()
    )
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bookmark)
    db.commit()
    return {"message": "Bookmark deleted"}


@router.get("", response_model=BookmarkListResponse)
def list_bookmarks(
    session_id: str,
    db: Session = Depends(get_db),
):
    """List all bookmarks for a session."""
    bookmarks = (
        db.query(Bookmark)
        .filter(Bookmark.session_id == session_id)
        .order_by(Bookmark.created_at.desc())
        .all()
    )
    return BookmarkListResponse(bookmarks=[BookmarkResponse.model_validate(b) for b in bookmarks])


@router.get("/check")
def check_bookmark(
    session_id: str,
    posting_url: str,
    db: Session = Depends(get_db),
):
    """Check if a job is bookmarked."""
    bookmark = (
        db.query(Bookmark)
        .filter(Bookmark.session_id == session_id, Bookmark.posting_url == posting_url)
        .first()
    )
    return {"bookmarked": bookmark is not None, "bookmark_id": bookmark.id if bookmark else None}
