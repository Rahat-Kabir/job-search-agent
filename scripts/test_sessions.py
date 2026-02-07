"""
Test script for session list and delete endpoints.

Requires: DATABASE_URL configured and server NOT running (tests directly against DB).
Usage: python scripts/test_sessions.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from backend.db.base import init_db, get_db
from backend.db.tables import ChatSession, ChatMessage


def test_session_crud():
    """Test creating, listing, and deleting sessions via DB directly."""
    init_db()
    db = next(get_db())

    # 1. Create a test session with messages
    session = ChatSession()
    db.add(session)
    db.commit()
    db.refresh(session)
    print(f"[OK] Created session: {session.id}")

    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content="Find me Python developer jobs in London",
        message_type="text",
    )
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content="I'll search for Python developer jobs in London.",
        message_type="text",
    )
    db.add_all([user_msg, assistant_msg])
    db.commit()
    print(f"[OK] Added 2 messages to session")

    # 2. List sessions — verify ours appears
    sessions = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
    session_ids = [s.id for s in sessions]
    assert session.id in session_ids, "Session not found in list"

    # Derive title from first user message
    first_user_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id, ChatMessage.role == "user")
        .order_by(ChatMessage.created_at)
        .first()
    )
    title = first_user_msg.content[:40] if first_user_msg else "New conversation"
    print(f"[OK] Session listed with title: '{title}'")

    # 3. Delete session
    msg_count = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count()
    assert msg_count == 2, f"Expected 2 messages, got {msg_count}"

    db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete()
    db.query(ChatSession).filter(ChatSession.id == session.id).delete()
    db.commit()

    # Verify deletion
    deleted_session = db.query(ChatSession).filter(ChatSession.id == session.id).first()
    assert deleted_session is None, "Session still exists after delete"

    remaining_msgs = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count()
    assert remaining_msgs == 0, f"Messages still exist: {remaining_msgs}"

    print(f"[OK] Session and messages deleted successfully")
    print("\nAll tests passed!")

    db.close()


if __name__ == "__main__":
    test_session_crud()
