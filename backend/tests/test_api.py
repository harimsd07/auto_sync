import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

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
