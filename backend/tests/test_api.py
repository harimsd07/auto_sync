import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base

@pytest_asyncio.fixture(autouse=True)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "1.0.0"}

@pytest.mark.asyncio
async def test_document_ingestion_and_chat_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Ingest document
        doc_payload = {
            "user_id": "test_user_1",
            "title": "Retrieval Augmented Generation Overview",
            "content": "Retrieval-Augmented Generation (RAG) is an AI framework that improves LLM responses by grounding them on external knowledge sources. It combines semantic vector search with prompt engineering.",
            "source": "manual_test"
        }
        res_doc = await ac.post("/api/v1/documents/upload-text", json=doc_payload)
        assert res_doc.status_code == 200
        doc_data = res_doc.json()
        assert doc_data["title"] == doc_payload["title"]
        assert doc_data["chunk_count"] >= 1

        # 2. List documents
        res_list = await ac.get("/api/v1/documents/?user_id=test_user_1")
        assert res_list.status_code == 200
        docs = res_list.json()
        assert len(docs) >= 1

        # 3. Stream chat request
        chat_payload = {
            "conversation_id": "conv_test_123",
            "user_id": "test_user_1",
            "message": "What is RAG?",
            "top_k": 3
        }
        res_chat = await ac.post("/api/v1/chat/stream", json=chat_payload)
        assert res_chat.status_code == 200
        assert "text/event-stream" in res_chat.headers["content-type"]
        assert "data:" in res_chat.text

@pytest.mark.asyncio
async def test_file_upload_and_feedback():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Upload binary text file
        files = {"file": ("test_doc.txt", b"Hybrid search combines BM25 keyword matching with vector cosine similarity for maximum accuracy.", "text/plain")}
        data = {"user_id": "test_user_2"}
        res_file = await ac.post("/api/v1/documents/upload-file", files=files, data=data)
        assert res_file.status_code == 200
        assert res_file.json()["title"] == "test_doc.txt"

        # Create conversation and get message
        conv_res = await ac.post("/api/v1/conversations/", json={"user_id": "test_user_2", "title": "Feedback Test"})
        assert conv_res.status_code == 200
        conv_id = conv_res.json()["id"]

        # Stream chat
        chat_res = await ac.post("/api/v1/chat/stream", json={"conversation_id": conv_id, "user_id": "test_user_2", "message": "Explain hybrid search"})
        assert chat_res.status_code == 200

        # Get messages to find assistant message ID
        msg_res = await ac.get(f"/api/v1/conversations/{conv_id}/messages")
        assert msg_res.status_code == 200
        msgs = msg_res.json()
        assert len(msgs) >= 2
        assistant_msg = next(m for m in msgs if m["role"] == "assistant")

        # Submit feedback rating
        fb_res = await ac.post(f"/api/v1/conversations/messages/{assistant_msg['id']}/feedback", json={"rating": 5, "feedback_text": "Great grounded response!"})
        assert fb_res.status_code == 200
        assert fb_res.json()["status"] == "success"
