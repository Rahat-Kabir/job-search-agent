"""Chat endpoint for conversational job search with HITL support."""

import json
from datetime import UTC, datetime
from typing import AsyncGenerator

from cachetools import TTLCache
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from sqlalchemy.orm import Session

from backend.agents.orchestrator import create_orchestrator_with_hitl, truncate_cv
from backend.api.limiter import limiter
from backend.api.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from backend.db import ChatMessage, ChatSession, Preferences, Profile, User, get_db
from backend.tools.pdf_parser import parse_pdf as parse_pdf_tool
from backend.utils.parser import parse_job_details_response, parse_jobs_response, parse_profile_response

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

router = APIRouter()


def _verify_session_access(session: ChatSession, x_user_id: str | None):
    """Verify the caller has access to this session.

    Rules:
    - If session has no user_id (anonymous): allow access (pre-CV-upload state)
    - If session has user_id: require matching X-User-ID header
    """
    if session.user_id is not None:
        if not x_user_id:
            raise HTTPException(status_code=403, detail="Authentication required for this session")
        if session.user_id != x_user_id:
            raise HTTPException(status_code=403, detail="Access denied")

# In-memory agent sessions (thread_id -> agent instance)
# Bounded TTL cache: max 200 agents, evict after 1 hour of inactivity.
# Evicted sessions are restored from PostgreSQL checkpointer on next request.
_agent_sessions: TTLCache = TTLCache(maxsize=200, ttl=3600)


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


def _tool_call_label(tool_names: list[str]) -> str:
    """Map tool call names to user-friendly labels."""
    labels = {
        "task": "Delegating to sub-agent...",
        "tavily_search": "Searching with Tavily...",
        "brave_search": "Searching with Brave...",
        "firecrawl_scrape": "Scraping job posting...",
        "write_file": "Saving results...",
        "read_file": "Reading saved data...",
    }
    for name in tool_names:
        if name in labels:
            return labels[name]
    return f"Calling {', '.join(tool_names)}..."


def _is_interrupt(result: dict) -> bool:
    """Check if agent result contains an interrupt request."""
    return "__interrupt__" in result and len(result["__interrupt__"]) > 0


def _extract_interrupt_info(result: dict) -> dict:
    """Extract human-readable info from an interrupt."""
    interrupts = result["__interrupt__"]
    interrupt = interrupts[0]
    value = getattr(interrupt, "value", interrupt) if not isinstance(interrupt, dict) else interrupt
    return {
        "tool_calls": value if isinstance(value, dict) else {"details": str(value)},
    }


def _process_agent_result(result: dict, is_detail_phase: bool = False) -> tuple[str, str, dict]:
    """Extract content, message_type, and extra_data from agent result.

    Returns (content, message_type, extra_data).
    """
    response_msgs = result.get("messages", [])
    agent_content = getattr(response_msgs[-1], "content", "") if response_msgs else ""

    message_type = "text"
    extra_data: dict = {}

    jobs = _extract_jobs_from_response(agent_content)
    if jobs:
        if is_detail_phase:
            # Phase 2: enriched jobs with details
            details = parse_job_details_response(agent_content)
            message_type = "jobs"
            extra_data = {"jobs": jobs, "details": details}
        else:
            # Phase 1: quick search results with selection UI
            message_type = "job_selection"
            extra_data = {"jobs": jobs}

    profile = _extract_profile_from_response(agent_content)
    if profile and not jobs:
        message_type = "profile"
        extra_data = {"profile": profile}

    return agent_content, message_type, extra_data


@router.post("/stream")
async def chat_stream(
    request: Request,
    data: ChatMessageRequest,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """Stream chat response via SSE with real-time agent events."""
    # Get or create session
    if data.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == data.session_id).first()
        if not session:
            session = ChatSession(id=data.session_id)
            db.add(session)
        else:
            _verify_session_access(session, x_user_id)
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

    async def event_generator() -> AsyncGenerator[str, None]:
        yield _sse_event("status", {"stage": "thinking", "message": "Processing your request..."})

        gen_db = next(get_db())
        try:
            agent, _ = _get_or_create_agent(thread_id)
            config = {"configurable": {"thread_id": thread_id}}

            # Build messages from history
            history = (
                gen_db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at)
                .all()
            )
            messages = [{"role": m.role, "content": m.content} for m in history]

            # Stream agent with real-time events
            last_chunk = None
            prev_msg_count = 0

            async for chunk in agent.astream(
                {"messages": messages},
                config=config,
                stream_mode="values",
            ):
                last_chunk = chunk
                msgs = chunk.get("messages", [])
                last_msg = msgs[-1] if msgs else None

                # Detect new messages (events) since last chunk
                if len(msgs) > prev_msg_count and last_msg:
                    msg_type = type(last_msg).__name__
                    tool_calls = getattr(last_msg, "tool_calls", [])

                    if tool_calls:
                        tool_names = [t.get("name", "unknown") for t in tool_calls]
                        # Map internal names to user-friendly labels
                        label = _tool_call_label(tool_names)
                        yield _sse_event("agent_event", {
                            "type": "tool_call",
                            "tools": tool_names,
                            "message": label,
                        })
                    elif msg_type == "ToolMessage":
                        yield _sse_event("agent_event", {
                            "type": "tool_result",
                            "message": "Processing results...",
                        })

                prev_msg_count = len(msgs)

                # Check for HITL interrupt
                if _is_interrupt(chunk):
                    interrupt_info = _extract_interrupt_info(chunk)

                    confirm_msg = ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content="I'd like to search for jobs matching your profile. This will call external search APIs. Approve to proceed?",
                        message_type="confirmation",
                        extra_data={"interrupt": interrupt_info},
                    )
                    gen_db.add(confirm_msg)
                    gen_db.commit()

                    yield _sse_event("confirmation", {
                        "session_id": session_id,
                        "requires_confirmation": True,
                        "message": {
                            "role": "assistant",
                            "content": confirm_msg.content,
                            "message_type": "confirmation",
                            "extra_data": {"interrupt": interrupt_info},
                            "created_at": confirm_msg.created_at.isoformat(),
                        },
                    })
                    return  # Stream ends at interrupt

            # No interrupt - extract final response
            if last_chunk:
                agent_content, message_type, extra_data = _process_agent_result(last_chunk)

                assistant_msg = ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=agent_content,
                    message_type=message_type,
                    extra_data=extra_data,
                )
                gen_db.add(assistant_msg)

                chat_session = gen_db.query(ChatSession).filter(ChatSession.id == session_id).first()
                if chat_session:
                    chat_session.updated_at = datetime.now(UTC)
                gen_db.commit()

                yield _sse_event("done", {
                    "session_id": session_id,
                    "user_id": chat_session.user_id if chat_session else None,
                    "message": {
                        "role": "assistant",
                        "content": agent_content,
                        "message_type": message_type,
                        "extra_data": extra_data,
                        "created_at": assistant_msg.created_at.isoformat(),
                    },
                })

        except Exception as e:
            import traceback
            error_msg = str(e) or f"{type(e).__name__}"
            tb = traceback.format_exc()
            print(f"[CHAT STREAM ERROR] {error_msg}\n{tb}")
            yield _sse_event("error", {"message": error_msg or "Unknown error - check server logs"})
        finally:
            gen_db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/confirm")
async def confirm_action(
    request: Request,
    data: dict,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """Confirm or reject a pending HITL action. Streams real-time events via SSE."""
    session_id = data.get("session_id")
    approved = data.get("approved", False)

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    _verify_session_access(session, x_user_id)

    thread_id = session.thread_id

    async def event_generator() -> AsyncGenerator[str, None]:
        if approved:
            yield _sse_event("status", {"stage": "searching", "message": "Approved! Searching for jobs..."})
        else:
            yield _sse_event("status", {"stage": "cancelled", "message": "Search cancelled."})

        gen_db = next(get_db())
        try:
            agent, _ = _get_or_create_agent(thread_id)
            config = {"configurable": {"thread_id": thread_id}}

            approve_decision = {"decisions": [{"type": "approve"}]}
            reject_decision = {"decisions": [{"type": "reject"}]}
            decision = approve_decision if approved else reject_decision

            # Stream with real-time events, auto-approving subsequent interrupts
            last_chunk = None
            while True:
                found_interrupt = False
                prev_msg_count = 0

                async for chunk in agent.astream(
                    Command(resume=decision),
                    config=config,
                    stream_mode="values",
                ):
                    last_chunk = chunk
                    msgs = chunk.get("messages", [])
                    last_msg = msgs[-1] if msgs else None

                    if len(msgs) > prev_msg_count and last_msg:
                        msg_type = type(last_msg).__name__
                        tool_calls = getattr(last_msg, "tool_calls", [])

                        if tool_calls:
                            tool_names = [t.get("name", "unknown") for t in tool_calls]
                            label = _tool_call_label(tool_names)
                            yield _sse_event("agent_event", {
                                "type": "tool_call",
                                "tools": tool_names,
                                "message": label,
                            })
                        elif msg_type == "ToolMessage":
                            yield _sse_event("agent_event", {
                                "type": "tool_result",
                                "message": "Processing results...",
                            })

                    prev_msg_count = len(msgs)

                    if _is_interrupt(chunk):
                        found_interrupt = True
                        yield _sse_event("agent_event", {
                            "type": "auto_approve",
                            "message": "Auto-approving follow-up search...",
                        })

                # After first approve, always auto-approve subsequent interrupts
                decision = approve_decision
                if not found_interrupt:
                    break

            # Extract final response
            if not approved:
                agent_content = "Search cancelled. Let me know if you'd like to try something else."
                message_type = "text"
                extra_data: dict = {}
            elif last_chunk:
                agent_content, message_type, extra_data = _process_agent_result(last_chunk)
            else:
                agent_content = "No results received."
                message_type = "text"
                extra_data = {}

            assistant_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=agent_content,
                message_type=message_type,
                extra_data=extra_data,
            )
            gen_db.add(assistant_msg)

            chat_session = gen_db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if chat_session:
                chat_session.updated_at = datetime.now(UTC)
            gen_db.commit()

            yield _sse_event("done", {
                "session_id": session_id,
                "user_id": chat_session.user_id if chat_session else None,
                "message": {
                    "role": "assistant",
                    "content": agent_content,
                    "message_type": message_type,
                    "extra_data": extra_data,
                    "created_at": assistant_msg.created_at.isoformat(),
                },
            })

        except Exception as e:
            yield _sse_event("error", {"message": str(e)})
        finally:
            gen_db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/get-details")
async def get_job_details(
    request: Request,
    data: dict,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """Get detailed info for selected jobs. Streams real-time events via SSE."""
    session_id = data.get("session_id")
    selected_urls = data.get("selected_urls", [])

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if not selected_urls:
        raise HTTPException(status_code=400, detail="selected_urls is required")

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    _verify_session_access(session, x_user_id)

    thread_id = session.thread_id

    async def event_generator() -> AsyncGenerator[str, None]:
        yield _sse_event("status", {"stage": "scraping", "message": f"Getting details for {len(selected_urls)} jobs..."})

        gen_db = next(get_db())
        try:
            agent, _ = _get_or_create_agent(thread_id)
            config = {"configurable": {"thread_id": thread_id}}

            # Save user selection as a message
            user_msg = ChatMessage(
                session_id=session_id,
                role="user",
                content=f"[Selected {len(selected_urls)} jobs for details]",
                message_type="text",
            )
            gen_db.add(user_msg)
            gen_db.commit()

            # Build history with detail request
            history = (
                gen_db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at)
                .all()
            )
            messages = [{"role": m.role, "content": m.content} for m in history]
            urls_text = "\n".join(f"- {url}" for url in selected_urls)
            messages[-1] = {"role": "user", "content": f"Get detailed information for these selected jobs:\n{urls_text}"}

            # Stream with real-time events, auto-approving firecrawl interrupts
            last_chunk = None
            approve_decision = {"decisions": [{"type": "approve"}]}

            # Initial stream
            async for chunk in agent.astream(
                {"messages": messages},
                config=config,
                stream_mode="values",
            ):
                last_chunk = chunk
                msgs = chunk.get("messages", [])
                last_msg = msgs[-1] if msgs else None

                if last_msg:
                    tool_calls = getattr(last_msg, "tool_calls", [])
                    if tool_calls:
                        tool_names = [t.get("name", "unknown") for t in tool_calls]
                        label = _tool_call_label(tool_names)
                        yield _sse_event("agent_event", {"type": "tool_call", "tools": tool_names, "message": label})
                    elif type(last_msg).__name__ == "ToolMessage":
                        yield _sse_event("agent_event", {"type": "tool_result", "message": "Processing scraped data..."})

                if _is_interrupt(chunk):
                    yield _sse_event("agent_event", {"type": "auto_approve", "message": "Auto-approving scrape..."})
                    break

            # Auto-approve loop for firecrawl interrupts
            while last_chunk and _is_interrupt(last_chunk):
                last_chunk = None
                async for chunk in agent.astream(
                    Command(resume=approve_decision),
                    config=config,
                    stream_mode="values",
                ):
                    last_chunk = chunk
                    msgs = chunk.get("messages", [])
                    last_msg = msgs[-1] if msgs else None

                    if last_msg:
                        tool_calls = getattr(last_msg, "tool_calls", [])
                        if tool_calls:
                            tool_names = [t.get("name", "unknown") for t in tool_calls]
                            label = _tool_call_label(tool_names)
                            yield _sse_event("agent_event", {"type": "tool_call", "tools": tool_names, "message": label})

                    if _is_interrupt(chunk):
                        yield _sse_event("agent_event", {"type": "auto_approve", "message": "Auto-approving scrape..."})

            # Extract final response
            if last_chunk:
                agent_content, message_type, extra_data = _process_agent_result(last_chunk, is_detail_phase=True)
            else:
                agent_content = "No details could be retrieved."
                message_type = "text"
                extra_data = {}

            assistant_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=agent_content,
                message_type=message_type,
                extra_data=extra_data,
            )
            gen_db.add(assistant_msg)

            chat_session = gen_db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if chat_session:
                chat_session.updated_at = datetime.now(UTC)
            gen_db.commit()

            yield _sse_event("done", {
                "session_id": session_id,
                "user_id": chat_session.user_id if chat_session else None,
                "message": {
                    "role": "assistant",
                    "content": agent_content,
                    "message_type": message_type,
                    "extra_data": extra_data,
                    "created_at": assistant_msg.created_at.isoformat(),
                },
            })

        except Exception as e:
            yield _sse_event("error", {"message": str(e)})
        finally:
            gen_db.close()

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
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """Send a message and get a response."""
    # Get or create session
    if data.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == data.session_id).first()
        if not session:
            session = ChatSession(id=data.session_id)
            db.add(session)
        else:
            _verify_session_access(session, x_user_id)
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

    # Invoke agent (async for AsyncPostgresSaver)
    result = await agent.ainvoke({"messages": messages}, config=config)

    # Handle interrupt
    if _is_interrupt(result):
        interrupt_info = _extract_interrupt_info(result)
        confirm_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content="I'd like to search for jobs matching your profile. Approve to proceed?",
            message_type="confirmation",
            extra_data={"interrupt": interrupt_info},
        )
        db.add(confirm_msg)
        db.commit()

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
                    extra_data=m.extra_data or {},
                    created_at=m.created_at,
                )
                for m in all_messages
            ],
        )

    # Normal response
    agent_content, message_type, extra_data = _process_agent_result(result)

    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=agent_content,
        message_type=message_type,
        extra_data=extra_data,
    )
    db.add(assistant_msg)

    session.updated_at = datetime.now(UTC)
    db.commit()

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
                extra_data=m.extra_data or {},
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
    x_user_id: str | None = Header(None, alias="X-User-ID"),
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
                extra_data={},
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
            _verify_session_access(session, x_user_id)
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
    result = await agent.ainvoke({"messages": messages}, config=config)

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


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """List chat sessions owned by the current authenticated user only."""
    if not x_user_id:
        return ChatSessionListResponse(sessions=[])

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == x_user_id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    result = []
    for s in sessions:
        first_user_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == s.id, ChatMessage.role == "user")
            .order_by(ChatMessage.created_at)
            .first()
        )
        content = first_user_msg.content if first_user_msg else ""
        result.append(ChatSessionResponse(
            id=s.id,
            title=content[:40] or "New conversation",
            preview=content[:80],
            created_at=s.created_at,
            updated_at=s.updated_at,
        ))

    return ChatSessionListResponse(sessions=result)


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """Delete a chat session and all its messages. Also cleans up in-memory agent."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    _verify_session_access(session, x_user_id)

    # Clean up in-memory agent
    thread_id = session.thread_id
    if thread_id in _agent_sessions:
        del _agent_sessions[thread_id]

    # Delete messages first (FK constraint), then session
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.query(ChatSession).filter(ChatSession.id == session_id).delete()
    db.commit()

    return {"deleted": True}


@router.get("/{session_id}", response_model=ChatResponse)
async def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    """Get chat history for a session."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        return ChatResponse(session_id=session_id, user_id=None, messages=[])

    _verify_session_access(session, x_user_id)

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

