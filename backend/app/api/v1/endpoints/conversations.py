from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.models.models import Conversation, Message, MessageFeedback

router = APIRouter()

class ConversationCreate(BaseModel):
    user_id: str = "default_user"
    title: Optional[str] = "New Chat Session"
    model_used: Optional[str] = "gpt-4o-mini"

class ConversationOut(BaseModel):
    id: str
    user_id: str
    title: str
    model_used: str
    created_at: str

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    msg_metadata: Optional[dict] = None
    created_at: str

class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = None

@router.post("/", response_model=ConversationOut)
async def create_conversation(req: ConversationCreate, db: AsyncSession = Depends(get_db)):
    conv = Conversation(
        user_id=req.user_id,
        title=req.title,
        model_used=req.model_used
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return {
        "id": conv.id,
        "user_id": conv.user_id,
        "title": conv.title,
        "model_used": conv.model_used or "gpt-4o-mini",
        "created_at": conv.created_at.isoformat()
    }

@router.get("/", response_model=List[ConversationOut])
async def list_conversations(user_id: str = "default_user", db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    convs = result.scalars().all()
    return [
        {
            "id": c.id,
            "user_id": c.user_id,
            "title": c.title or "Chat Session",
            "model_used": c.model_used or "gpt-4o-mini",
            "created_at": c.created_at.isoformat()
        }
        for c in convs
    ]

@router.get("/{conv_id}/messages", response_model=List[MessageOut])
async def get_conversation_messages(conv_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
    )
    msgs = result.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "msg_metadata": m.msg_metadata,
            "created_at": m.created_at.isoformat()
        }
        for m in msgs
    ]

@router.post("/messages/{message_id}/feedback")
async def record_message_feedback(
    message_id: str,
    fb: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalars().first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    feedback = MessageFeedback(
        message_id=message_id,
        rating=fb.rating,
        feedback_text=fb.feedback_text
    )
    db.add(feedback)
    await db.commit()
    return {"status": "success", "message_id": message_id, "rating": fb.rating}

@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Conversation).where(Conversation.id == conv_id))
    await db.commit()
    return None
