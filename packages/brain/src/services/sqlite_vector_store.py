"""
SQLite Vector Store for Mu2 Cognitive OS
Uses SQLite with vector similarity - much lighter than Postgres+pgvector
Suitable for resource-constrained systems
"""

import asyncio
from typing import List, Dict, Any, Optional
import requests
import sqlite3
import numpy as np
from pathlib import Path

from src.core.config import settings


class SQLiteVectorStore:
    """Lightweight vector store using SQLite"""

    def __init__(self, db_path: str = "/tmp/mu2_vectors.db"):
        self.db_path = db_path
        self._embedding_cache: Dict[str, List[float]] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize the SQLite database"""
        if self._initialized:
            return

        # Create connection and setup table
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create table with content and embedding (stored as BLOB)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS textbook_chunks (
                id TEXT PRIMARY KEY,
                chapter_id TEXT NOT NULL,
                section_id TEXT NOT NULL,
                content TEXT NOT NULL,
                grade_level INTEGER DEFAULT 8,
                subject TEXT DEFAULT 'science',
                metadata TEXT DEFAULT '{}',
                embedding BLOB
            )
        """)

        # Create index on content for keyword search
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_content
            ON textbook_chunks(content)
        """)

        conn.commit()
        conn.close()

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

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0

    def _query_vector_store(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the vector store using cosine similarity
        Loads all embeddings and calculates similarity in-memory
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all chunks with embeddings
        cursor.execute("SELECT * FROM textbook_chunks WHERE embedding IS NOT NULL")
        rows = cursor.fetchall()

        results = []
        query_vec = np.array(query_embedding)

        for row in rows:
            # Convert BLOB to numpy array
            stored_embedding = np.frombuffer(row["embedding"], dtype=np.float32)

            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_vec, stored_embedding)

            results.append({
                "id": row["id"],
                "content": row["content"],
                "score": float(similarity),
                "metadata": {
                    "chapter_id": row["chapter_id"],
                    "section_id": row["section_id"],
                    "grade_level": row["grade_level"],
                    "subject": row["subject"],
                }
            })

        conn.close()

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def retrieve_facts(
        self, query: str, top_k: int = 5, similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Retrieve specific, factual information using vector similarity search"""
        await self.ensure_initialized()

        loop = asyncio.get_event_loop()

        def query_facts():
            query_embedding = self._get_embedding(query)
            results = self._query_vector_store(query_embedding, top_k)
            return [r for r in results if r["score"] >= similarity_threshold]

        return await loop.run_in_executor(None, query_facts)

    async def retrieve_concepts(
        self, query: str, top_k: int = 5, similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Retrieve abstract, conceptual information using broader vector search"""
        await self.ensure_initialized()

        loop = asyncio.get_event_loop()

        def query_concepts():
            query_embedding = self._get_embedding(query)
            results = self._query_vector_store(query_embedding, top_k)
            return [r for r in results if r["score"] >= similarity_threshold]

        return await loop.run_in_executor(None, query_concepts)

    async def retrieve_hybrid(
        self, query: str, top_k: int = 5, chunk_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Hybrid retrieval without strict filtering"""
        await self.ensure_initialized()

        loop = asyncio.get_event_loop()

        def query_hybrid():
            query_embedding = self._get_embedding(query)
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

            # Check database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM textbook_chunks")
            count = cursor.fetchone()[0]
            conn.close()

            return {
                "status": "healthy",
                "embedding_model": settings.embedding_model,
                "embedding_dimension": len(test_embedding),
                "vector_store_type": "sqlite",
                "chunks_count": count,
                "db_path": self.db_path,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global singleton instance
sqlite_vector_store = SQLiteVectorStore()
