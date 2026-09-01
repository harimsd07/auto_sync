from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.models.models import Document, DocumentChunk, User
from app.services.chunking import chunking_service
from app.services.vector_store import vector_store

router = APIRouter()

class DocumentOut(BaseModel):
    id: str
    title: str
    source: Optional[str]
    file_type: Optional[str]
    file_size: Optional[int]
    embedding_status: str
    chunk_count: int
    created_at: str

class TextUploadRequest(BaseModel):
    user_id: str
    title: str
    content: str
    source: Optional[str] = "manual"

@router.post("/upload-text", response_model=DocumentOut)
async def upload_text_document(req: TextUploadRequest, db: AsyncSession = Depends(get_db)):
    doc = Document(
        user_id=req.user_id,
        title=req.title,
        content=req.content,
        source=req.source,
        file_type="text/plain",
        file_size=len(req.content.encode('utf-8')),
        embedding_status="completed"
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Process chunking & vector embeddings
    chunks_data = chunking_service.split_text(req.content)
    chunk_objects = []

    for item in chunks_data:
        vector_id = f"vec-{doc.id}-{item['chunk_index']}"
        
        # Save to Vector Store
        await vector_store.upsert(
            vector_id=vector_id,
            text=item["content"],
            metadata={
                "document_id": doc.id,
                "user_id": req.user_id,
                "title": req.title,
                "chunk_index": item["chunk_index"]
            }
        )

        chunk_obj = DocumentChunk(
            document_id=doc.id,
            chunk_index=item["chunk_index"],
            content=item["content"],
            token_count=item["token_count"],
            vector_id=vector_id,
            embedding_model="text-embedding-3-small"
        )
        chunk_objects.append(chunk_obj)

    db.add_all(chunk_objects)
    await db.commit()

    return {
        "id": doc.id,
        "title": doc.title,
        "source": doc.source,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "embedding_status": doc.embedding_status,
        "chunk_count": len(chunk_objects),
        "created_at": doc.created_at.isoformat()
    }

@router.get("/", response_model=List[DocumentOut])
async def list_documents(user_id: str = "default_user", db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.user_id == user_id))
    docs = result.scalars().all()
    
    out = []
    for doc in docs:
        chunk_res = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        chunks = chunk_res.scalars().all()
        out.append({
            "id": doc.id,
            "title": doc.title,
            "source": doc.source,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "embedding_status": doc.embedding_status,
            "chunk_count": len(chunks),
            "created_at": doc.created_at.isoformat()
        })
    return out

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc_id))
    chunks = result.scalars().all()
    for chunk in chunks:
        if chunk.vector_id:
            await vector_store.delete(chunk.vector_id)
            
    await db.execute(delete(Document).where(Document.id == doc_id))
    await db.commit()
    return None
