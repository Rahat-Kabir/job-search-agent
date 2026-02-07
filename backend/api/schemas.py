"""API request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


# Profile schemas
class SkillResponse(BaseModel):
    name: str
    confidence: float
    source: str


class ProfileResponse(BaseModel):
    skills: list[SkillResponse]
    experience_years: int | None
    job_titles: list[str]
    summary: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


# Preferences schemas
class PreferencesUpdate(BaseModel):
    location_type: str | None = Field(default=None, description="remote/onsite/hybrid/any")
    target_roles: list[str] | None = None
    excluded_companies: list[str] | None = None
    min_salary: int | None = None


class PreferencesResponse(BaseModel):
    location_type: str
    target_roles: list[str]
    excluded_companies: list[str]
    min_salary: int | None

    class Config:
        from_attributes = True


# Search schemas
class SearchRequest(BaseModel):
    queries: list[str] | None = Field(default=None, description="Custom queries (optional)")


class JobResultResponse(BaseModel):
    id: str
    title: str
    company: str
    match_score: float
    match_reason: str
    location_type: str
    salary: str | None
    posting_url: str
    description_snippet: str

    class Config:
        from_attributes = True


class SearchResultsResponse(BaseModel):
    search_id: str
    status: str
    results: list[JobResultResponse]
    created_at: datetime
    completed_at: datetime | None


# CV upload
class CVUploadResponse(BaseModel):
    user_id: str
    profile: ProfileResponse
    message: str


# Chat schemas
class ChatMessageRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    message_type: str = "text"
    extra_data: dict = {}
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    session_id: str
    user_id: str | None
    messages: list[ChatMessageResponse]


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    preview: str
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionResponse]


# Bookmark schemas
class BookmarkCreate(BaseModel):
    session_id: str
    title: str
    company: str
    match_score: float = 0.0
    match_reason: str = ""
    location_type: str = "unknown"
    salary: str | None = None
    posting_url: str
    description_snippet: str = ""


class BookmarkResponse(BaseModel):
    id: str
    session_id: str
    title: str
    company: str
    match_score: float
    match_reason: str
    location_type: str
    salary: str | None
    posting_url: str
    description_snippet: str
    created_at: datetime

    class Config:
        from_attributes = True


class BookmarkListResponse(BaseModel):
    bookmarks: list[BookmarkResponse]
