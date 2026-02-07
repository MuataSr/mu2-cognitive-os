"""
Simple Vector Store for Mu2 Cognitive OS
Uses direct SQL queries with fresh connections - no connection pooling
Suitable for resource-constrained systems
"""

import asyncio
from typing import List, Dict, Any, Optional
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from src.core.config import settings


class SimpleVectorStore:
    """Lightweight vector store using direct SQL queries"""

    def __init__(self):
        self._embedding_cache: Dict[str, List[float]] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize the vector store"""
        if self._initialized:
            return
        self._initialized = True

    async def ensure_initialized(self):
        """Ensure the service is initialized"""
        if not self._initialized:
            await self.initialize()

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama (synchronous)"""
        # Check cache first
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        # Call Ollama API
        response = requests.post(
            f"{settings.llm_base_url}/api/embeddings",
            json={"model": settings.embedding_model, "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        embedding = response.json()["embedding"]

        # Cache the result
        self._embedding_cache[text] = embedding
        return embedding

    def _query_vector_store(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the vector store using raw SQL with cosine similarity
        Creates a fresh connection for each query
        """
        # Create engine with no pooling (fresh connection each time)
        engine = create_engine(
            settings.database_url,
            poolclass=QueuePool,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
        )

        try:
            with engine.connect() as conn:
                # Convert embedding to PostgreSQL array string format for pgvector
                embedding_array = "{" + ",".join(f"{x:.6f}" for x in query_embedding) + "}"

                # Use pgvector's cosine similarity operator
                # Note: <=> returns negative distance, so we negate to get similarity
                query = text("""
                    SELECT
                        id,
                        chapter_id,
                        section_id,
                        content,
                        grade_level,
                        subject,
                        metadata,
                        -1 * (embedding <=> :embedding::vector) as similarity
                    FROM cortex.textbook_chunks
                    ORDER BY embedding <=> :embedding::vector
                    LIMIT :top_k
                """)

                result = conn.execute(
                    query,
                    {"embedding": embedding_array, "top_k": top_k}
                )

                rows = result.fetchall()

                results = []
                for row in rows:
                    results.append({
                        "id": str(row[0]),
                        "content": row[3],
                        "score": float(row[7]),
                        "metadata": {
                            "chapter_id": row[1],
                            "section_id": row[2],
                            "grade_level": row[4],
                            "subject": row[5],
                            **row[6]
                        }
                    })

                return results
        finally:
            engine.dispose()

    async def retrieve_facts(
        self, query: str, top_k: int = 5, similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Retrieve specific, factual information using vector similarity search
        """
        await self.ensure_initialized()

        # Run blocking operations in executor
        loop = asyncio.get_event_loop()

        def query_facts():
            # Get embedding
            query_embedding = self._get_embedding(query)

            # Query vector store
            results = self._query_vector_store(query_embedding, top_k)

            # Filter by threshold
            return [r for r in results if r["score"] >= similarity_threshold]

        return await loop.run_in_executor(None, query_facts)

    async def retrieve_concepts(
        self, query: str, top_k: int = 5, similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve abstract, conceptual information using broader vector search
        """
        await self.ensure_initialized()

        # Run blocking operations in executor
        loop = asyncio.get_event_loop()

        def query_concepts():
            # Get embedding
            query_embedding = self._get_embedding(query)

            # Query vector store
            results = self._query_vector_store(query_embedding, top_k)

            # Filter by threshold (lower for concepts)
            return [r for r in results if r["score"] >= similarity_threshold]

        return await loop.run_in_executor(None, query_concepts)

    async def retrieve_hybrid(
        self, query: str, top_k: int = 5, chunk_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval without strict filtering
        """
        await self.ensure_initialized()

        # Run blocking operations in executor
        loop = asyncio.get_event_loop()

        def query_hybrid():
            # Get embedding
            query_embedding = self._get_embedding(query)

            # Query vector store
            return self._query_vector_store(query_embedding, top_k)

        return await loop.run_in_executor(None, query_hybrid)

    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a text string"""
        await self.ensure_initialized()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_embedding, text)

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the vector store service"""
        try:
            await self.ensure_initialized()

            # Test embedding
            test_embedding = await self.get_embedding("test")

            # Test database connection
            engine = create_engine(settings.database_url, poolclass=QueuePool, pool_size=1)
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                db_ok = True
            except Exception as e:
                db_ok = False
                db_error = str(e)
            finally:
                engine.dispose()

            if not db_ok:
                return {
                    "status": "unhealthy",
                    "error": f"Database connection failed: {db_error}"
                }

            return {
                "status": "healthy",
                "embedding_model": settings.embedding_model,
                "embedding_dimension": len(test_embedding),
                "vector_store_type": "simple_sql",
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global singleton instance
simple_vector_store = SimpleVectorStore()
