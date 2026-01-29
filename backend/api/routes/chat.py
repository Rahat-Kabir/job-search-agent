"""Chat endpoint for conversational job search."""

import asyncio
import json
from datetime import UTC, datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.agents.orchestrator import create_orchestrator_with_hitl, truncate_cv
from backend.api.limiter import limiter
from backend.api.schemas import ChatMessageRequest, ChatMessageResponse, ChatResponse
from backend.db import ChatMessage, ChatSession, Preferences, Profile, User, get_db
from backend.tools.pdf_parser import parse_pdf as parse_pdf_tool
from backend.utils.parser import parse_jobs_response, parse_profile_response

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

router = APIRouter()

# In-memory agent sessions (thread_id -> agent instance)
_agent_sessions: dict[str, tuple] = {}


def _get_or_create_agent(thread_id: str):
    """Get or create an agent for a thread."""
    if thread_id not in _agent_sessions:
        agent, checkpointer = create_orchestrator_with_hitl()
        _agent_sessions[thread_id] = (agent, checkpointer)
    return _agent_sessions[thread_id]


def _extract_jobs_from_response(content: str) -> list[dict] | None:
    """Try to extract jobs from agent response."""
    jobs = parse_jobs_response(content)
    if jobs and len(jobs) > 0:
        return jobs
    return None


def _extract_profile_from_response(content: str) -> dict | None:
    """Try to extract profile from agent response."""
    profile = parse_profile_response(content)
    if profile.get("skills") or profile.get("summary"):
        return profile
    return None


def _sse_event(event: str, data: dict) -> str:
    """Format SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _invoke_agent_sync(
    thread_id: str,
    message: str,
    session_id: str,
    db_session_factory,
) -> dict:
    """Synchronous agent invocation (runs in thread pool)."""
    # Create new DB session for this thread
    # db_session_factory is get_session_factory, which returns a sessionmaker
    # We need to call it twice: once to get sessionmaker, once to get session
    db = db_session_factory()()
    try:
        agent, _ = _get_or_create_agent(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        # Build messages from history
        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )
        messages = [{"role": m.role, "content": m.content} for m in history]

        # Invoke agent
        result = agent.invoke({"messages": messages}, config=config)
        response_msgs = result.get("messages", [])
        agent_content = getattr(response_msgs[-1], "content", "") if response_msgs else ""

        # Determine message type and extract extra_data
        message_type = "text"
        extra_data: dict = {}

        jobs = _extract_jobs_from_response(agent_content)
        if jobs:
            message_type = "jobs"
            extra_data = {"jobs": jobs}

        profile = _extract_profile_from_response(agent_content)
        if profile and not jobs:
            message_type = "profile"
            extra_data = {"profile": profile}

        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=agent_content,
            message_type=message_type,
            extra_data=extra_data,
        )
        db.add(assistant_msg)

        # Update session timestamp
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.updated_at = datetime.now(UTC)
        db.commit()

        return {
            "session_id": session_id,
            "user_id": session.user_id if session else None,
            "message": {
                "role": "assistant",
                "content": agent_content,
                "message_type": message_type,
                "extra_data": extra_data,
                "created_at": assistant_msg.created_at.isoformat(),
            },
        }
    finally:
        db.close()


@router.post("/stream")
async def chat_stream(
    request: Request,
    data: ChatMessageRequest,
    db: Session = Depends(get_db),
):
    """Stream chat response via SSE."""
    from backend.db.base import get_session_factory

    # Get or create session
    if data.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == data.session_id).first()
        if not session:
            session = ChatSession(id=data.session_id)
            db.add(session)
    else:
        session = ChatSession()
        db.add(session)

    db.commit()
    db.refresh(session)

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=data.message,
        message_type="text",
    )
    db.add(user_msg)
    db.commit()

    session_id = session.id
    thread_id = session.thread_id
    user_message = data.message

    async def event_generator() -> AsyncGenerator[str, None]:
        # Yield initial status
        yield _sse_event("status", {"stage": "thinking", "message": "Processing your request..."})

        # Run agent in thread pool (non-blocking)
        loop = asyncio.get_event_loop()
        result_future = loop.run_in_executor(
            None,  # default executor
            _invoke_agent_sync,
            thread_id,
            user_message,
            session_id,
            get_session_factory,
        )

        # Send heartbeat while waiting
        stages = [
            (1.0, "analyzing", "Analyzing your message..."),
            (3.0, "working", "Working on it..."),
            (6.0, "searching", "Searching for information..."),
            (10.0, "processing", "Still processing..."),
        ]
        start_time = asyncio.get_event_loop().time()
        stage_idx = 0

        while not result_future.done():
            await asyncio.sleep(0.3)
            elapsed = asyncio.get_event_loop().time() - start_time

            # Send next stage if time elapsed
            if stage_idx < len(stages) and elapsed >= stages[stage_idx][0]:
                _, stage, msg = stages[stage_idx]
                yield _sse_event("status", {"stage": stage, "message": msg})
                stage_idx += 1

        # Get result
        try:
            agent_response = await asyncio.wrap_future(result_future)
            yield _sse_event("done", agent_response)
        except Exception as e:
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("", response_model=ChatResponse)
@limiter.limit("5/minute")
async def chat(
    request: Request,
    data: ChatMessageRequest,
    db: Session = Depends(get_db),
):
    """Send a message and get a response."""
    # Get or create session
    if data.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == data.session_id).first()
        if not session:
            session = ChatSession(id=data.session_id)
            db.add(session)
    else:
        session = ChatSession()
        db.add(session)

    db.commit()
    db.refresh(session)

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=data.message,
        message_type="text",
    )
    db.add(user_msg)
    db.commit()

    # Get agent and invoke
    agent, _ = _get_or_create_agent(session.thread_id)
    config = {"configurable": {"thread_id": session.thread_id}}

    # Build messages from history
    history = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.id
    ).order_by(ChatMessage.created_at).all()

    messages = [{"role": m.role, "content": m.content} for m in history]

    # Invoke agent
    result = agent.invoke({"messages": messages}, config=config)
    response_msgs = result.get("messages", [])
    agent_content = getattr(response_msgs[-1], "content", "") if response_msgs else ""

    # Determine message type and extract extra_data
    message_type = "text"
    extra_data: dict = {}

    jobs = _extract_jobs_from_response(agent_content)
    if jobs:
        message_type = "jobs"
        extra_data = {"jobs": jobs}

    profile = _extract_profile_from_response(agent_content)
    if profile and not jobs:
        message_type = "profile"
        extra_data = {"profile": profile}

    # Save assistant message
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=agent_content,
        message_type=message_type,
        extra_data=extra_data,
    )
    db.add(assistant_msg)

    # Update session timestamp
    session.updated_at = datetime.now(UTC)
    db.commit()

    # Return all messages
    all_messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.id
    ).order_by(ChatMessage.created_at).all()

    return ChatResponse(
        session_id=session.id,
        user_id=session.user_id,
        messages=[
            ChatMessageResponse(
                role=m.role,
                content=m.content,
                message_type=m.message_type,
                metadata=m.metadata or {},
                created_at=m.created_at,
            )
            for m in all_messages
        ],
    )


@router.post("/upload", response_model=ChatResponse)
@limiter.limit("3/minute")
async def chat_with_cv(
    request: Request,
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Upload CV and start chat."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        # Return error as chat message
        session = ChatSession() if not session_id else (
            db.query(ChatSession).filter(ChatSession.id == session_id).first() or ChatSession()
        )
        db.add(session)
        db.commit()

        error_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content="Please upload a PDF file.",
            message_type="text",
        )
        db.add(error_msg)
        db.commit()

        return ChatResponse(
            session_id=session.id,
            user_id=None,
            messages=[ChatMessageResponse(
                role="assistant",
                content="Please upload a PDF file.",
                message_type="text",
                metadata={},
                created_at=error_msg.created_at,
            )],
        )

    # Check file size
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5 MB.")

    # Parse PDF
    cv_text = parse_pdf_tool.invoke({"pdf_content": content})
    cv_text = truncate_cv(cv_text, max_chars=4000)

    # Get or create session
    if session_id:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            session = ChatSession(id=session_id)
            db.add(session)
    else:
        session = ChatSession()
        db.add(session)

    db.commit()
    db.refresh(session)

    # Save user message (CV upload)
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=f"[Uploaded CV: {file.filename}]",
        message_type="text",
    )
    db.add(user_msg)
    db.commit()

    # Get agent and invoke with CV
    agent, _ = _get_or_create_agent(session.thread_id)
    config = {"configurable": {"thread_id": session.thread_id}}

    messages = [{"role": "user", "content": f"Here's my CV:\n\n{cv_text}"}]
    result = agent.invoke({"messages": messages}, config=config)

    response_msgs = result.get("messages", [])
    agent_content = getattr(response_msgs[-1], "content", "") if response_msgs else ""

    # Extract profile
    profile_data = parse_profile_response(agent_content)

    # Create user and save profile if extracted
    user_id = None
    if profile_data.get("skills"):
        user = User()
        db.add(user)
        db.commit()

        user_id = user.id
        session.user_id = user_id

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

        preferences = Preferences(user_id=user.id)
        db.add(preferences)

    # Save assistant message
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=agent_content,
        message_type="profile" if profile_data.get("skills") else "text",
        extra_data={"profile": profile_data} if profile_data.get("skills") else {},
    )
    db.add(assistant_msg)

    session.updated_at = datetime.now(UTC)
    db.commit()

    # Return all messages
    all_messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.id
    ).order_by(ChatMessage.created_at).all()

    return ChatResponse(
        session_id=session.id,
        user_id=user_id,
        messages=[
            ChatMessageResponse(
                role=m.role,
                content=m.content,
                message_type=m.message_type,
                extra_data=m.extra_data or {},
                created_at=m.created_at,
            )
            for m in all_messages
        ],
    )


@router.get("/{session_id}", response_model=ChatResponse)
async def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Get chat history for a session."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        return ChatResponse(session_id=session_id, user_id=None, messages=[])

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at).all()

    return ChatResponse(
        session_id=session.id,
        user_id=session.user_id,
        messages=[
            ChatMessageResponse(
                role=m.role,
                content=m.content,
                message_type=m.message_type,
                extra_data=m.extra_data or {},
                created_at=m.created_at,
            )
            for m in messages
        ],
    )
