# Development Plan: RAG-Based Chatbot System

This document outlines a structured, phased development plan based on the architecture and specifications defined in [RAG_CHATBOT_DESIGN.md](file:///home/irah/kodela_autosync/RAG_CHATBOT_DESIGN.md). The plan spans initial core infrastructure setup through MVP development, enhancement, enterprise scaling, and production deployment.

---

## User Review Required

> [!IMPORTANT]
> **Key Architecture Decisions Needed from User:**
> 1. **Backend Tech Stack Choice**: Python (FastAPI + LangChain/LlamaIndex) vs Node.js (NestJS / Express). *Recommendation: Python 3.11+ with FastAPI for native ML/embedding library ecosystem support.*
> 2. **Vector DB Provider**: Managed (Pinecone) vs Self-hosted / Open Source (Weaviate / Qdrant / pgvector). *Recommendation: Weaviate or pgvector for MVP to keep ops low while enabling hybrid search.*
> 3. **LLM Provider & Model**: OpenAI API (`gpt-4o` / `gpt-4o-mini`) vs Anthropic (`claude-3-5-sonnet`) vs LiteLLM multi-provider abstraction layer. *Recommendation: OpenAI + LiteLLM abstraction layer.*

---

## Open Questions

> [!NOTE]
> - **Primary Document Types**: What file formats will be ingested initially (PDF, DOCX, Markdown, HTML scraping)?
> - **Target Deployment Platform**: AWS (ECS/EKS), GCP (Cloud Run/GKE), or local/Docker container deployment?

---

## Proposed Technical Implementation Phases

### Phase 0: Project Setup & Infrastructure Blueprint
Establish repository structure, containerized dependencies, and core configuration management.

- **Infrastructure Configuration**:
  - `docker-compose.yml` for PostgreSQL 16 (+ `pgvector`), Redis 7, and local Vector DB (e.g. Weaviate/Qdrant).
  - Environment management (`.env.example`) with secrets validation.
- **Backend Initial Scaffold**:
  - FastAPI application layout (`app/api`, `app/core`, `app/services`, `app/models`, `app/db`).
  - SQLAlchemy 2.0 / AsyncPG connection setup + Alembic database migrations.
- **Frontend Initial Scaffold**:
  - Next.js 14 (App Router) + TypeScript + Tailwind CSS design system with Dark Mode support.

---

### Phase 1: Core MVP RAG Engine & Basic Interface
Build end-to-end document ingestion, embedding generation, vector search, and streaming LLM chat.

#### Component 1.1: Database Schemas & Migrations
#### [NEW] `backend/app/models/user.py`
#### [NEW] `backend/app/models/document.py`
#### [NEW] `backend/app/models/conversation.py`
#### [NEW] `backend/app/models/message.py`
- Implement PostgreSQL schemas for `users`, `api_keys`, `documents`, `document_chunks`, `conversations`, `messages`, and `retrieved_documents` as detailed in [RAG_CHATBOT_DESIGN.md Section 4.1](file:///home/irah/kodela_autosync/RAG_CHATBOT_DESIGN.md#L343-L468).

#### Component 1.2: Ingestion & Embedding Pipeline
#### [NEW] `backend/app/services/ingestion.py`
#### [NEW] `backend/app/services/chunking.py`
#### [NEW] `backend/app/services/vector_store.py`
- Implement document parsing (PDF, TXT, MD, DOCX).
- Token-aware chunking strategy (default chunk size: 1000 characters, overlap: 200 characters).
- Integrate embedding model interface (OpenAI `text-embedding-3-small` / `sentence-transformers`).
- Upsert embeddings and metadata into Vector DB and PostgreSQL.

#### Component 1.3: Retrieval & Chat Engine
#### [NEW] `backend/app/services/retrieval.py`
#### [NEW] `backend/app/services/llm.py`
#### [NEW] `backend/app/api/v1/endpoints/chat.py`
- Implement similarity retrieval (`top_k` chunk retrieval).
- Construct context-augmented prompts combining system instructions, chat history, and retrieved document chunks.
- Stream LLM responses via Server-Sent Events (SSE) / WebSockets to the client.

#### Component 1.4: Frontend Chat & Document Upload Interface
#### [NEW] `frontend/src/app/chat/page.tsx`
#### [NEW] `frontend/src/components/chat/ChatWindow.tsx`
#### [NEW] `frontend/src/components/documents/UploadModal.tsx`
- Interactive web UI for chatting with real-time text streaming.
- UI for document drag-and-drop upload and processing status display.
- Source citation visualization highlighting retrieved text snippets.

---

### Phase 2: Enhanced Hybrid Search & Management UI
Upgrade retrieval quality and management capabilities.

#### Component 2.1: Hybrid Search & Reranking
#### [NEW] `backend/app/services/hybrid_search.py`
- Combine Vector Cosine Similarity (70% weight) with PostgreSQL BM25 Full-Text Search (30% weight).
- Reciprocal Rank Fusion (RRF) / weighted score normalization for combined top results.
- Optional Cross-Encoder reranking step to maximize precision before LLM context construction.

#### Component 2.2: Management UI & History
#### [NEW] `frontend/src/components/documents/DocumentList.tsx`
#### [NEW] `frontend/src/components/chat/SidebarHistory.tsx`
#### [NEW] `frontend/src/app/admin/page.tsx`
- Sidebar with conversation history management (create, delete, title auto-generation).
- Document management page with status indicators, metadata viewing, and delete capabilities.
- Basic Admin Dashboard for system metrics (documents ingested, token consumption, query volume).

---

### Phase 3: Scale, Security & Enterprise Features
Harden the system for high concurrency and secure enterprise access.

#### Component 3.1: Security & Auth
#### [NEW] `backend/app/core/security.py`
#### [NEW] `backend/app/api/v1/endpoints/auth.py`
- JWT authentication (access & refresh tokens) + password hashing via passlib/argon2.
- Role-Based Access Control (RBAC: Admin, User, Viewer) and document-level permissions.
- API Key management for programmatic integrations.

#### Component 3.2: Performance & Caching
#### [NEW] `backend/app/core/redis.py`
#### [NEW] `backend/app/services/cache.py`
- Multi-tier caching: Redis caching for session state, rate-limiting tokens, and repeated query results.
- Celery / Bull async task queues for background document parsing and embedding jobs.

---

### Phase 4: Production Hardening, Monitoring & DevOps
Deploy to production with complete observability and CI/CD pipelines.

#### Component 4.1: DevOps Infrastructure
#### [NEW] `docker/Dockerfile.backend`
#### [NEW] `docker/Dockerfile.frontend`
#### [NEW] `.github/workflows/ci-cd.yml`
- Containerized builds for frontend and backend services.
- GitHub Actions pipeline for automated linting, unit testing, Docker image building, and staging deployment.

#### Component 4.2: Observability & Health
#### [NEW] `backend/app/core/telemetry.py`
- Prometheus metrics endpoint (`/metrics`) tracking latency (p50, p95, p99), LLM token usage, and error rates.
- Health check endpoints (`/healthz`, `/readyz`).

---

## Verification Plan

### Automated Tests
- **Backend Unit & Integration Tests**:
  `pytest backend/tests/` (unit tests for chunking, vector embedding, and prompt formatting).
- **API Endpoint Verification**:
  `pytest backend/tests/test_api.py` (authentication flows, document uploads, streaming message endpoint).
- **Frontend Unit Tests**:
  `npm run test` (Jest / React Testing Library for components).
- **End-to-End Tests**:
  `npx playwright test` (testing user upload -> indexing -> chat response flow).

### Manual Verification
1. **Document Ingestion Test**: Upload sample PDF & Markdown files, verify status changes to `completed`, and inspect vector DB entries.
2. **Retrieval Accuracy Test**: Submit queries referencing uploaded document content and check that source citations accurate match original text.
3. **Streaming & UX Test**: Verify response streaming behavior, smooth UI updates, dark mode toggle, and error handling.
