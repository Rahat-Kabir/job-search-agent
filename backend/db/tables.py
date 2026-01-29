"""Database table models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    """User account."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    profile: Mapped["Profile | None"] = relationship(back_populates="user", uselist=False)
    preferences: Mapped["Preferences | None"] = relationship(back_populates="user", uselist=False)
    searches: Mapped[list["SearchSession"]] = relationship(back_populates="user")


class Profile(Base):
    """User profile extracted from CV."""

    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    skills: Mapped[dict] = mapped_column(JSON, default=list)  # List of Skill dicts
    experience_years: Mapped[int | None] = mapped_column(default=None)
    job_titles: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    cv_text: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship(back_populates="profile")


class Preferences(Base):
    """User search preferences."""

    __tablename__ = "preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    location_type: Mapped[str] = mapped_column(String(20), default="any")  # remote/onsite/hybrid/any
    target_roles: Mapped[list] = mapped_column(JSON, default=list)
    excluded_companies: Mapped[list] = mapped_column(JSON, default=list)
    min_salary: Mapped[int | None] = mapped_column(default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship(back_populates="preferences")


class SearchSession(Base):
    """A job search session."""

    __tablename__ = "search_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/running/completed/failed
    queries: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    user: Mapped["User"] = relationship(back_populates="searches")
    results: Mapped[list["JobResult"]] = relationship(back_populates="search_session")


class JobResult(Base):
    """A job search result."""

    __tablename__ = "job_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    search_id: Mapped[str] = mapped_column(ForeignKey("search_sessions.id"))
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    match_score: Mapped[float] = mapped_column(Float)
    match_reason: Mapped[str] = mapped_column(Text)
    location_type: Mapped[str] = mapped_column(String(20), default="unknown")
    salary: Mapped[str | None] = mapped_column(String(100), default=None)
    posting_url: Mapped[str] = mapped_column(Text)
    description_snippet: Mapped[str] = mapped_column(Text, default="")

    search_session: Mapped["SearchSession"] = relationship(back_populates="results")


class ChatSession(Base):
    """A chat session with conversation history."""

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    thread_id: Mapped[str] = mapped_column(String(36), default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    """A message in a chat session."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"))
    role: Mapped[str] = mapped_column(String(20))  # user, assistant
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(20), default="text")  # text, jobs, profile
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
