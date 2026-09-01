import re
import numpy as np
from typing import List, Dict, Any, Optional
from app.core.config import settings

class InMemoryVectorStore:
    def __init__(self):
        self.vectors: Dict[str, Dict[str, Any]] = {} # id -> {vector, metadata, content}

    def _mock_embedding(self, text: str) -> List[float]:
        """Generates deterministic pseudo-embeddings for testing/offline mode."""
        np.random.seed(abs(hash(text)) % (2**32))
        vec = np.random.randn(1536)
        norm = np.linalg.norm(vec)
        return (vec / norm).tolist()

    async def get_embedding(self, text: str) -> List[float]:
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-openai-api-key-here":
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                resp = await client.embeddings.create(
                    input=text,
                    model=settings.DEFAULT_EMBEDDING_MODEL
                )
                return resp.data[0].embedding
            except Exception as e:
                print(f"OpenAI Embedding API error, falling back to local generator: {e}")
        return self._mock_embedding(text)

    async def upsert(self, vector_id: str, text: str, metadata: Dict[str, Any]) -> str:
        vector = await self.get_embedding(text)
        self.vectors[vector_id] = {
            "id": vector_id,
            "vector": vector,
            "text": text,
            "metadata": metadata
        }
        return vector_id

    def _calculate_keyword_score(self, query_terms: List[str], text: str) -> float:
        """Calculates normalized keyword term-frequency score."""
        if not query_terms or not text:
            return 0.0
        text_lower = text.lower()
        matches = sum(1 for term in query_terms if term in text_lower)
        return matches / max(1, len(query_terms))

    async def search(
        self,
        query_text: str,
        top_k: int = 5,
        filter_user_id: Optional[str] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        if not self.vectors:
            return []
            
        query_vector = np.array(await self.get_embedding(query_text))
        query_terms = [w.lower() for w in re.findall(r'\w+', query_text) if len(w) > 2]
        
        results = []

        for vector_id, item in self.vectors.items():
            if filter_user_id and item["metadata"].get("user_id") != filter_user_id:
                continue
                
            # 1. Vector similarity score (Cosine)
            doc_vec = np.array(item["vector"])
            vec_score = float(np.dot(query_vector, doc_vec))
            
            # 2. Lexical keyword score
            kw_score = self._calculate_keyword_score(query_terms, item["text"])
            
            # 3. Hybrid weighted score
            final_hybrid_score = (vec_score * vector_weight) + (kw_score * keyword_weight)
            
            results.append({
                "vector_id": vector_id,
                "score": final_hybrid_score,
                "vector_score": round(vec_score, 4),
                "keyword_score": round(kw_score, 4),
                "content": item["text"],
                "metadata": item["metadata"]
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def delete(self, vector_id: str):
        if vector_id in self.vectors:
            del self.vectors[vector_id]

vector_store = InMemoryVectorStore()
