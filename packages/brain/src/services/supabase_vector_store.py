"""
Supabase Vector Store - Mu2 Cognitive OS
========================================

Stores questions in Supabase with pgvector support for semantic search.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio
import logging
import json

from src.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Models
# ============================================================================

class Question(BaseModel):
    """A question stored in Supabase"""
    id: Optional[str] = None
    question_id: str
    question_text: str
    question_type: str  # 'multiple_choice', 'true_false', 'short_answer'
    subject: str
    topic: Optional[str] = None
    difficulty: str = "medium"
    grade_level: int = 8
    correct_answer: str
    incorrect_answers: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    distractor1: Optional[str] = None
    distractor2: Optional[str] = None
    distractor3: Optional[str] = None
    source: str = "sciq"  # 'sciq', 'science_bowl', 'opentdb'
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class QuestionSearchResult(BaseModel):
    """Result from question search"""
    id: str
    question_id: str
    question_text: str
    question_type: str
    subject: str
    topic: Optional[str]
    difficulty: str
    correct_answer: str
    incorrect_answers: List[str]
    explanation: Optional[str]
    source: str
    similarity: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Supabase Vector Store
# ============================================================================

class SupabaseVectorStore:
    """
    Vector store using Supabase with pgvector extension

    Uses psycopg2 for database operations with pgvector support.
    """

    def __init__(self):
        """Initialize the Supabase vector store"""
        self.database_url = settings.database_url
        self._initialized = False

    async def initialize(self):
        """Initialize database connection"""
        if self._initialized:
            return

        # Test connection
        await self._with_connection(lambda conn: None)
        self._initialized = True
        logger.info("Supabase vector store initialized with pgvector")

    async def _with_connection(self, callback):
        """Execute a callback with a database connection"""
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        conn = psycopg2.connect(self.database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        try:
            return callback(conn)
        finally:
            conn.close()

    async def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using local Ollama

        Args:
            text: Text to embed

        Returns:
            Embedding vector (768-dim for nomic-embed-text)
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.llm_base_url}/api/embeddings",
                json={
                    "model": settings.embedding_model,
                    "prompt": text
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])

    def _embedding_to_pgvector(self, embedding: List[float]) -> str:
        """Convert embedding list to pgvector string format"""
        return f"[{','.join(map(str, embedding))}]"

    async def add_question(
        self,
        question: Question,
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        Add a question to the database with embedding

        Args:
            question: Question to add
            embedding: Pre-computed embedding (computed if not provided)

        Returns:
            ID of inserted question
        """
        await self.initialize()

        # Generate embedding if not provided
        if embedding is None:
            embedding = await self._get_embedding(question.question_text)

        # Convert embedding to pgvector format
        embedding_str = self._embedding_to_pgvector(embedding)

        def insert_question(conn):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cortex.questions (
                    question_id,
                    question_text,
                    question_type,
                    subject,
                    topic,
                    difficulty,
                    grade_level,
                    correct_answer,
                    incorrect_answers,
                    explanation,
                    distractor1,
                    distractor2,
                    distractor3,
                    source,
                    metadata,
                    embedding
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector
                )
                ON CONFLICT (question_id, source)
                DO UPDATE SET
                    question_text = EXCLUDED.question_text,
                    embedding = EXCLUDED.embedding,
                    updated_at = NOW()
                RETURNING id
            """, (
                question.question_id,
                question.question_text,
                question.question_type,
                question.subject,
                question.topic,
                question.difficulty,
                question.grade_level,
                question.correct_answer,
                question.incorrect_answers,
                question.explanation,
                question.distractor1,
                question.distractor2,
                question.distractor3,
                question.source,
                json.dumps(question.metadata) if question.metadata else '{}',
                embedding_str
            ))
            row = cursor.fetchone()
            return row[0] if row else None

        return await self._with_connection(insert_question)

    async def add_questions_batch(
        self,
        questions: List[Question],
        embeddings: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Add multiple questions in batch

        Args:
            questions: List of questions to add
            embeddings: Pre-computed embeddings (computed if not provided)

        Returns:
            Dict with success count and errors
        """
        success_count = 0
        errors = []

        for i, question in enumerate(questions):
            try:
                embedding = embeddings[i] if embeddings else None
                await self.add_question(question, embedding)
                success_count += 1
            except Exception as e:
                logger.error(f"Error adding question {question.question_id}: {e}")
                errors.append(f"{question.question_id}: {str(e)}")

        return {
            "success": success_count,
            "failed": len(errors),
            "errors": errors
        }

    async def search_similar_questions(
        self,
        query: str,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.6
    ) -> List[QuestionSearchResult]:
        """
        Search for similar questions using semantic search

        Args:
            query: Search query text
            subject: Filter by subject
            topic: Filter by topic
            difficulty: Filter by difficulty
            source: Filter by source
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of similar questions with similarity scores
        """
        await self.initialize()

        # Generate query embedding
        query_embedding = await self._get_embedding(query)
        embedding_str = self._embedding_to_pgvector(query_embedding)

        # Build dynamic query
        def search_query(conn):
            cursor = conn.cursor()

            # Build WHERE clause parameters
            params = []
            conditions = ["embedding IS NOT NULL"]
            param_idx = 1

            if subject:
                conditions.append(f"subject = %s")
                params.append(subject)
                param_idx += 1

            if topic:
                conditions.append(f"topic = %s")
                params.append(topic)
                param_idx += 1

            if difficulty:
                conditions.append(f"difficulty = %s")
                params.append(difficulty)
                param_idx += 1

            if source:
                conditions.append(f"source = %s")
                params.append(source)
                param_idx += 1

            where_clause = " AND ".join(conditions)

            # Build full SQL with parameters
            # We need 4 embedding placeholders and 1 each for threshold, limit
            sql = f"""
                SELECT
                    id,
                    question_id,
                    question_text,
                    question_type,
                    subject,
                    topic,
                    difficulty,
                    correct_answer,
                    incorrect_answers,
                    explanation,
                    source,
                    1 - (embedding <=> %s::vector) as similarity
                FROM cortex.questions
                WHERE {where_clause}
                AND (1 - (embedding <=> %s::vector)) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """

            # Parameters: embedding (x3 for <=>, >=, ORDER), threshold, limit
            sql_params = params + [embedding_str, embedding_str, threshold, embedding_str, limit]

            cursor.execute(sql, sql_params)

            return cursor.fetchall()

        rows = await self._with_connection(search_query)

        return [
            QuestionSearchResult(
                id=row[0],
                question_id=row[1],
                question_text=row[2],
                question_type=row[3],
                subject=row[4],
                topic=row[5],
                difficulty=row[6],
                correct_answer=row[7],
                incorrect_answers=row[8] or [],
                explanation=row[9],
                source=row[10],
                similarity=float(row[11])
            )
            for row in rows
        ]

    async def get_random_questions(
        self,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 10
    ) -> List[Question]:
        """
        Get random questions (useful for quizzes)

        Args:
            subject: Filter by subject
            topic: Filter by topic
            difficulty: Filter by difficulty
            source: Filter by source
            limit: Maximum results

        Returns:
            List of random questions
        """
        await self.initialize()

        def random_query(conn):
            cursor = conn.cursor()

            # Build WHERE clause parameters
            params = []
            conditions = []
            param_idx = 1

            if subject:
                conditions.append(f"subject = %s")
                params.append(subject)
                param_idx += 1

            if topic:
                conditions.append(f"topic = %s")
                params.append(topic)
                param_idx += 1

            if difficulty:
                conditions.append(f"difficulty = %s")
                params.append(difficulty)
                param_idx += 1

            if source:
                conditions.append(f"source = %s")
                params.append(source)
                param_idx += 1

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            params.append(limit)

            cursor.execute(f"""
                SELECT
                    id,
                    question_id,
                    question_text,
                    question_type,
                    subject,
                    topic,
                    difficulty,
                    correct_answer,
                    incorrect_answers,
                    explanation,
                    source
                FROM cortex.questions
                WHERE {where_clause}
                ORDER BY RANDOM()
                LIMIT %s
            """, params)

            return cursor.fetchall()

        rows = await self._with_connection(random_query)

        return [
            Question(
                id=row[0],
                question_id=row[1],
                question_text=row[2],
                question_type=row[3],
                subject=row[4],
                topic=row[5],
                difficulty=row[6],
                correct_answer=row[7],
                incorrect_answers=row[8] or [],
                explanation=row[9],
                source=row[10]
            )
            for row in rows
        ]

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get question statistics from database

        Returns:
            Dict with statistics by source and subject
        """
        await self.initialize()

        def stats_query(conn):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    source,
                    subject,
                    COUNT(*) as total_questions,
                    SUM(CASE WHEN difficulty = 'easy' THEN 1 ELSE 0 END) as easy_count,
                    SUM(CASE WHEN difficulty = 'medium' THEN 1 ELSE 0 END) as medium_count,
                    SUM(CASE WHEN difficulty = 'hard' THEN 1 ELSE 0 END) as hard_count
                FROM cortex.questions
                GROUP BY source, subject
                ORDER BY source, subject
            """)
            return cursor.fetchall()

        rows = await self._with_connection(stats_query)

        stats_by_source = []
        total = 0
        for row in rows:
            total += row[2]
            stats_by_source.append({
                "source": row[0],
                "subject": row[1],
                "total": row[2],
                "easy": row[3] or 0,
                "medium": row[4] or 0,
                "hard": row[5] or 0
            })

        return {
            "by_source_subject": stats_by_source,
            "total_questions": total
        }

    async def get_question_by_id(self, question_id: str, source: str) -> Optional[Question]:
        """
        Get a specific question by ID

        Args:
            question_id: External question ID
            source: Source of the question

        Returns:
            Question or None if not found
        """
        await self.initialize()

        def get_query(conn):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    id,
                    question_id,
                    question_text,
                    question_type,
                    subject,
                    topic,
                    difficulty,
                    correct_answer,
                    incorrect_answers,
                    explanation,
                    source
                FROM cortex.questions
                WHERE question_id = %s AND source = %s
                LIMIT 1
            """, (question_id, source))
            return cursor.fetchone()

        row = await self._with_connection(get_query)

        if row:
            return Question(
                id=row[0],
                question_id=row[1],
                question_text=row[2],
                question_type=row[3],
                subject=row[4],
                topic=row[5],
                difficulty=row[6],
                correct_answer=row[7],
                incorrect_answers=row[8] or [],
                explanation=row[9],
                source=row[10]
            )
        return None

    async def get_topics(self, subject: Optional[str] = None) -> List[str]:
        """
        Get list of unique topics

        Args:
            subject: Filter by subject (optional)

        Returns:
            List of topic names
        """
        await self.initialize()

        def topics_query(conn):
            cursor = conn.cursor()
            if subject:
                cursor.execute("""
                    SELECT DISTINCT topic
                    FROM cortex.questions
                    WHERE subject = %s
                    AND topic IS NOT NULL
                    ORDER BY topic
                """, (subject,))
            else:
                cursor.execute("""
                    SELECT DISTINCT topic
                    FROM cortex.questions
                    WHERE topic IS NOT NULL
                    ORDER BY topic
                """)
            return cursor.fetchall()

        rows = await self._with_connection(topics_query)
        return [row[0] for row in rows]

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the vector store

        Returns:
            Health status dict
        """
        try:
            await self.initialize()

            # Test embedding
            test_embedding = await self._get_embedding("test")

            # Get question count
            stats = await self.get_statistics()

            return {
                "status": "healthy",
                "vector_store_type": "supabase_pgvector",
                "embedding_model": settings.embedding_model,
                "embedding_dimension": len(test_embedding),
                "total_questions": stats.get("total_questions", 0),
                "is_supabase": settings.is_supabase()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "vector_store_type": "supabase_pgvector"
            }


# ============================================================================
# Singleton Instance
# ============================================================================

_supabase_vector_store: Optional[SupabaseVectorStore] = None


def get_supabase_vector_store() -> SupabaseVectorStore:
    """Get the singleton Supabase vector store instance"""
    global _supabase_vector_store
    if _supabase_vector_store is None:
        _supabase_vector_store = SupabaseVectorStore()
    return _supabase_vector_store


# ============================================================================
# Convenience Functions
# ============================================================================

async def search_questions(
    query: str,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 10
) -> List[QuestionSearchResult]:
    """
    Search for similar questions

    Usage:
        results = await search_questions(
            query="What is photosynthesis?",
            subject="Biology",
            limit=5
        )
    """
    store = get_supabase_vector_store()
    return await store.search_similar_questions(
        query=query,
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        source=source,
        limit=limit
    )


async def get_random_quiz_questions(
    subject: str,
    difficulty: str = "medium",
    count: int = 10
) -> List[Question]:
    """
    Get random questions for a quiz

    Usage:
        questions = await get_random_quiz_questions(
            subject="Physics",
            difficulty="medium",
            count=10
        )
    """
    store = get_supabase_vector_store()
    return await store.get_random_questions(
        subject=subject,
        difficulty=difficulty,
        limit=count
    )
