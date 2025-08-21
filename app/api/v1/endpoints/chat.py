from __future__ import annotations
from fastapi import APIRouter, Request, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.chat import (
    ChatRouteIn,
    ChatRouteOut,
    ChatSessionCreate,
    ChatSessionOut,
    ChatMessageCreate,
    ChatMessageOut,
    ChatMessagesPage,
)
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.chat import ChatSession, ChatMessage

router = APIRouter()


@router.post("/chat/route", response_model=ChatRouteOut)
async def route_intent(req: Request, data: ChatRouteIn, _user=Depends(get_current_user)) -> ChatRouteOut:
    orchestrator = req.app.state.orchestrator
    result = await orchestrator.route(data.intent, data.payload)
    return ChatRouteOut(**result)


@router.post("/chat/sessions", response_model=ChatSessionOut)
def create_session(
    body: ChatSessionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ChatSessionOut:
    if body.reuse_recent:
        existing = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user.id, ChatSession.status == "open")
            .order_by(ChatSession.last_activity_at.desc())
            .first()
        )
        if existing:
            return ChatSessionOut(id=existing.id, status=existing.status, last_activity_at=existing.last_activity_at)
    cs = ChatSession(user_id=user.id, status="open")
    db.add(cs)
    db.commit()
    db.refresh(cs)
    return ChatSessionOut(id=cs.id, status=cs.status, last_activity_at=cs.last_activity_at)


@router.get("/chat/sessions/{session_id}/messages", response_model=ChatMessagesPage)
def list_messages(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ChatMessagesPage:
    # Ensure session belongs to user
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess or (sess.user_id and sess.user_id != user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    q = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    items = [
        ChatMessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            audio_url=m.audio_url,
            created_at=m.created_at,
        )
        for m in rows
    ]
    return ChatMessagesPage(items=items)


@router.post("/chat/sessions/{session_id}/messages", response_model=ChatMessageOut)
async def create_message(
    session_id: int,
    body: ChatMessageCreate,
    req: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ChatMessageOut:
    # Validate session ownership
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess or (sess.user_id and sess.user_id != user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if not body.content and not body.audio_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="content or audio_url required")

    # Persist user message
    content = body.content or ""
    msg = ChatMessage(session_id=session_id, role="user", content=content, audio_url=body.audio_url)
    db.add(msg)
    sess.last_activity_at = sess.last_activity_at  # will be updated by DB default on new message or remain
    db.commit()
    db.refresh(msg)

    # Whisper + LLM routing stubs
    if body.audio_url and not body.content:
        # call whisper client to transcribe (stubbed)
        try:
            from app.services.whisper_client import transcribe

            transcript = await transcribe(body.audio_url)
            content = transcript or ""
        except Exception:
            content = ""

    # Use Orchestrator to route intent if we later extract intents; for now simple echo or LLM stub
    try:
        from app.services.llm_client import complete

        reply_text = await complete(prompt=content, session_id=session_id)
    except Exception:
        reply_text = ""

    # Save agent reply
    reply = ChatMessage(session_id=session_id, role="agent", content=reply_text or "")
    db.add(reply)
    db.commit()
    db.refresh(reply)

    return ChatMessageOut(
        id=reply.id,
        role=reply.role,
        content=reply.content,
        audio_url=reply.audio_url,
        created_at=reply.created_at,
    )
