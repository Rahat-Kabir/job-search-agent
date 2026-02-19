"""Bookmark endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.api.schemas import BookmarkCreate, BookmarkListResponse, BookmarkResponse
from backend.db import Bookmark, ChatSession, get_db

router = APIRouter()


def _verify_session_owner(db: Session, session_id: str, x_user_id: str | None):
    """Verify the caller owns the session associated with this bookmark.

    Rules:
    - If session has no user_id (anonymous): allow access
    - If session has user_id: require matching X-User-ID header
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session and session.user_id is not None:
        if not x_user_id:
            raise HTTPException(status_code=403, detail="Authentication required")
        if session.user_id != x_user_id:
            raise HTTPException(status_code=403, detail="Access denied")


@router.post("", response_model=BookmarkResponse)
def create_bookmark(
    bookmark: BookmarkCreate,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """Create a new bookmark."""
    _verify_session_owner(db, bookmark.session_id, x_user_id)

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
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """Delete a bookmark by ID."""
    bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    _verify_session_owner(db, bookmark.session_id, x_user_id)

    db.delete(bookmark)
    db.commit()
    return {"message": "Bookmark deleted"}


@router.delete("/url/{session_id}")
def delete_bookmark_by_url(
    session_id: str,
    posting_url: str,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """Delete a bookmark by session_id and posting_url."""
    _verify_session_owner(db, session_id, x_user_id)

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
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """List all bookmarks for a session."""
    _verify_session_owner(db, session_id, x_user_id)

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
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """Check if a job is bookmarked."""
    _verify_session_owner(db, session_id, x_user_id)

    bookmark = (
        db.query(Bookmark)
        .filter(Bookmark.session_id == session_id, Bookmark.posting_url == posting_url)
        .first()
    )
    return {"bookmarked": bookmark is not None, "bookmark_id": bookmark.id if bookmark else None}
