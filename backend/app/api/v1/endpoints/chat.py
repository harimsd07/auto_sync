import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.models import Conversation, Message
from app.services.llm_rag import llm_rag_service

router = APIRouter()

class ChatRequest(BaseModel):
    conversation_id: str
    user_id: str = "default_user"
    message: str
    top_k: Optional[int] = 4

@router.post("/stream")
async def chat_stream_endpoint(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    # 1. Verify conversation exists or auto-create
    result = await db.execute(select(Conversation).where(Conversation.id == req.conversation_id))
    conv = result.scalars().first()
    if not conv:
        conv = Conversation(id=req.conversation_id, user_id=req.user_id, title=req.message[:30] + "...")
        db.add(conv)
        await db.commit()
    elif conv.title == "New Chat Session" or conv.title == "New Conversation":
        conv.title = req.message[:30] + "..."
        await db.commit()

    # 2. Save user message to database
    user_msg = Message(
        conversation_id=req.conversation_id,
        role="user",
        content=req.message
    )
    db.add(user_msg)
    await db.commit()

    # 3. Load historical messages for context window
    msg_history_res = await db.execute(
        select(Message)
        .where(Message.conversation_id == req.conversation_id)
        .order_by(Message.created_at.asc())
    )
    history_records = msg_history_res.scalars().all()
    history_formatted = [{"role": m.role, "content": m.content} for m in history_records[:-1]]

    # 4. Define streaming generator
    async def sse_event_generator():
        accumulated_assistant_response = ""
        sources_metadata = []

        async for event in llm_rag_service.generate_rag_response_stream(
            query=req.message,
            chat_history=history_formatted,
            user_id=req.user_id,
            top_k=req.top_k or 4
        ):
            if event["type"] == "sources":
                sources_metadata = event["data"]
                yield f"data: {json.dumps({'type': 'sources', 'data': sources_metadata})}\n\n"
            elif event["type"] == "delta":
                delta = event["data"]
                accumulated_assistant_response += delta
                yield f"data: {json.dumps({'type': 'delta', 'data': delta})}\n\n"
            elif event["type"] == "end":
                # Save assistant message to database
                async with AsyncSession(db.bind) as save_session:
                    assistant_msg = Message(
                        conversation_id=req.conversation_id,
                        role="assistant",
                        content=accumulated_assistant_response,
                        msg_metadata={"sources": sources_metadata}
                    )
                    save_session.add(assistant_msg)
                    await save_session.commit()
                
                yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")
