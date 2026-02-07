"""
Question Pipeline - Mu2 Cognitive OS
===================================

Import and process ADAPT questions into local vector store.

Flow:
1. Fetch from ADAPT API
2. Anonymize (remove any PII)
3. Store in local Supabase
4. Generate embeddings (local only!)
5. Index in vector store

FERPA COMPLIANCE:
- All questions stored locally
- No PII in question data
- Embeddings generated locally via Ollama
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from src.services.adapt_client import LibreTextsADAPT, Question, QuestionFilter
from src.services.anonymization_service import anonymization_service
from src.services.sqlite_vector_store import sqlite_vector_store

logger = logging.getLogger(__name__)


# ============================================================================
# Pipeline Models
# ============================================================================

class ImportedQuestion(BaseModel):
    """A question imported from ADAPT and stored locally"""
    id: str
    question_id: str  # Original ADAPT ID
    text: str
    type: str
    subject: str
    difficulty: str
    topic: str
    options: Optional[List[str]] = None
    explanation: Optional[str] = None
    embedding: Optional[List[float]] = None
    source: str = "adapt"
    imported_at: datetime = Field(default_factory=datetime.utcnow)


class ImportResult(BaseModel):
    """Result of importing questions"""
    total_fetched: int
    successfully_imported: int
    failed: int
    errors: List[str] = Field(default_factory=list)
    imported_ids: List[str] = Field(default_factory=list)
    duration_seconds: float


class QuestionIndex(BaseModel):
    """Indexed question for retrieval"""
    question_id: str
    text: str
    subject: str
    topic: str
    difficulty: str
    embedding: List[float]
    metadata: Dict[str, Any]


# ============================================================================
# Question Pipeline
# ============================================================================

class QuestionPipeline:
    """
    Import and process ADAPT questions into local vector store

    This pipeline:
    1. Fetches questions from ADAPT API
    2. Anonymizes any potential PII
    3. Generates embeddings using local Ollama
    4. Stores in SQLite vector store
    5. Creates database records for tracking
    """

    def __init__(
        self,
        adapt_client: Optional[LibreTextsADAPT] = None,
        batch_size: int = 10
    ):
        """
        Initialize the question pipeline

        Args:
            adapt_client: ADAPT API client (uses singleton if None)
            batch_size: Number of questions to process per batch
        """
        self.adapt_client = adapt_client
        self.batch_size = batch_size

    async def import_topic_questions(
        self,
        topic: str,
        subject: str = "Biology",
        difficulty: str = "medium",
        count: int = 50
    ) -> ImportResult:
        """
        Import all questions for a topic

        Args:
            topic: Topic to import (e.g., "Photosynthesis")
            subject: Subject area (e.g., "Biology")
            difficulty: Difficulty level
            count: Maximum number of questions to import

        Returns:
            ImportResult with statistics
        """
        start_time = datetime.utcnow()
        errors = []
        imported_ids = []
        success_count = 0
        failed_count = 0

        try:
            # Step 1: Fetch questions from ADAPT
            if self.adapt_client:
                # Use provided client
                async with self.adapt_client:
                    filters = QuestionFilter(
                        subject=subject,
                        topic=topic,
                        difficulty=difficulty,
                        count=count
                    )
                    questions = await self.adapt_client.get_questions(filters)
            else:
                # Use singleton client
                from src.services.adapt_client import get_adapt_client
                client = get_adapt_client()
                filters = QuestionFilter(
                    subject=subject,
                    topic=topic,
                    difficulty=difficulty,
                    count=count
                )
                questions = await client.get_questions(filters)

            total_fetched = len(questions)

            if total_fetched == 0:
                return ImportResult(
                    total_fetched=0,
                    successfully_imported=0,
                    failed=0,
                    errors=["No questions found for the given criteria"],
                    duration_seconds=(datetime.utcnow() - start_time).total_seconds()
                )

            logger.info(f"Fetched {total_fetched} questions from ADAPT for topic: {topic}")

            # Step 2: Process in batches
            for i in range(0, len(questions), self.batch_size):
                batch = questions[i:i + self.batch_size]
                batch_results = await self._process_batch(batch)

                success_count += batch_results["success"]
                failed_count += batch_results["failed"]
                errors.extend(batch_results["errors"])
                imported_ids.extend(batch_results["imported_ids"])

            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"Import complete: {success_count}/{total_fetched} questions "
                f"imported in {duration:.2f}s"
            )

            return ImportResult(
                total_fetched=total_fetched,
                successfully_imported=success_count,
                failed=failed_count,
                errors=errors,
                imported_ids=imported_ids,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Error importing questions: {e}")
            return ImportResult(
                total_fetched=0,
                successfully_imported=0,
                failed=0,
                errors=[str(e)],
                duration_seconds=(datetime.utcnow() - start_time).total_seconds()
            )

    async def _process_batch(
        self,
        questions: List[Question]
    ) -> Dict[str, Any]:
        """
        Process a batch of questions

        Args:
            questions: List of questions to process

        Returns:
            Dict with success, failed, errors, imported_ids
        """
        success = 0
        failed = 0
        errors = []
        imported_ids = []

        for question in questions:
            try:
                # Step 1: Anonymize question text (remove any potential PII)
                anonymized_result = await anonymization_service.anonymize_text(
                    text=question.text,
                    user_id=None,  # No user context for questions
                    include_metadata=False
                )
                question_text = anonymized_result.anonymized_text

                # Step 2: Generate embedding using local Ollama
                embedding = await self._generate_embedding(question_text)

                # Step 3: Store in vector store
                await self._store_question(question, question_text, embedding)

                imported_ids.append(question.question_id)
                success += 1

            except Exception as e:
                logger.error(f"Error processing question {question.question_id}: {e}")
                errors.append(f"{question.question_id}: {str(e)}")
                failed += 1

        return {
            "success": success,
            "failed": failed,
            "errors": errors,
            "imported_ids": imported_ids
        }

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for question text using local Ollama

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Use the vector store's embedding function
        # This ensures we use the same model as retrieval
        from src.services.sqlite_vector_store import sqlite_vector_store

        # The vector store has an embed_text method
        result = await sqlite_vector_store.embed_text(text)

        if isinstance(result, list) and len(result) > 0:
            return result[0]  # Return first (and only) embedding
        else:
            # Fallback: generate embedding directly
            import httpx

            # Call Ollama embedding API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/api/embeddings",
                    json={
                        "model": "nomic-embed-text",
                        "prompt": text
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [])

    async def _store_question(
        self,
        question: Question,
        question_text: str,
        embedding: List[float]
    ) -> None:
        """
        Store question in vector store

        Args:
            question: Original question object
            question_text: Anonymized question text
            embedding: Generated embedding vector
        """
        # Store in vector store for semantic search
        await sqlite_vector_store.add_texts(
            texts=[question_text],
            metadatas=[{
                "type": "question",
                "question_id": question.question_id,
                "subject": question.subject,
                "topic": question.topic,
                "difficulty": question.difficulty,
                "question_type": question.type,
                "source": "adapt"
            }],
            embeddings=[embedding]
        )

    async def search_similar_questions(
        self,
        query: str,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar questions in the local store

        Args:
            query: Search query
            subject: Optional subject filter
            topic: Optional topic filter
            top_k: Number of results to return

        Returns:
            List of matching questions with metadata
        """
        # Generate embedding for query
        query_embedding = await self._generate_embedding(query)

        # Search vector store
        results = await sqlite_vector_store.similarity_search(
            query_text=query,
            query_embedding=query_embedding,
            top_k=top_k,
            filter_dict={
                "type": "question",
                **({"subject": subject} if subject else {}),
                **({"topic": topic} if topic else {})
            }
        )

        return results

    async def get_question_by_id(
        self,
        question_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific question by ID

        Args:
            question_id: The ADAPT question ID

        Returns:
            Question data or None if not found
        """
        # Search for the question
        results = await sqlite_vector_store.retrieve_facts(
            query=question_id,
            top_k=1
        )

        for result in results:
            metadata = result.get("metadata", {})
            if metadata.get("question_id") == question_id:
                return result

        return None

    async def get_imported_topics(self, subject: Optional[str] = None) -> List[str]:
        """
        Get list of topics that have been imported

        Args:
            subject: Optional subject filter

        Returns:
            List of topic names
        """
        # Query vector store for unique topics
        # This is a simplified version - in production, use a proper database query
        results = await sqlite_vector_store.retrieve_facts(
            query="question topic",
            top_k=100
        )

        topics = set()
        for result in results:
            metadata = result.get("metadata", {})
            if metadata.get("type") == "question":
                result_subject = metadata.get("subject")
                result_topic = metadata.get("topic")

                if subject is None or result_subject == subject:
                    if result_topic:
                        topics.add(result_topic)

        return sorted(list(topics))

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about imported questions

        Returns:
            Dict with count by subject, topic, etc.
        """
        results = await sqlite_vector_store.retrieve_facts(
            query="question",
            top_k=1000
        )

        stats = {
            "total": 0,
            "by_subject": {},
            "by_topic": {},
            "by_difficulty": {}
        }

        for result in results:
            metadata = result.get("metadata", {})
            if metadata.get("type") == "question":
                stats["total"] += 1

                subject = metadata.get("subject", "unknown")
                topic = metadata.get("topic", "unknown")
                difficulty = metadata.get("difficulty", "unknown")

                stats["by_subject"][subject] = stats["by_subject"].get(subject, 0) + 1
                stats["by_topic"][topic] = stats["by_topic"].get(topic, 0) + 1
                stats["by_difficulty"][difficulty] = stats["by_difficulty"].get(difficulty, 0) + 1

        return stats


# ============================================================================
# Singleton Instance
# ============================================================================

_question_pipeline: Optional[QuestionPipeline] = None


def get_question_pipeline() -> QuestionPipeline:
    """Get the singleton question pipeline instance"""
    global _question_pipeline
    if _question_pipeline is None:
        _question_pipeline = QuestionPipeline()
    return _question_pipeline


# ============================================================================
# Convenience Functions
# ============================================================================

async def import_questions_for_topic(
    topic: str,
    subject: str = "Biology",
    difficulty: str = "medium",
    count: int = 50
) -> ImportResult:
    """
    Import questions from ADAPT for a specific topic

    Usage:
        result = await import_questions_for_topic(
            topic="Photosynthesis",
            subject="Biology",
            difficulty="medium",
            count=50
        )
        print(f"Imported {result.successfully_imported} questions")
    """
    pipeline = get_question_pipeline()
    return await pipeline.import_topic_questions(
        topic=topic,
        subject=subject,
        difficulty=difficulty,
        count=count
    )


async def search_questions(
    query: str,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Search for similar questions in the local store

    Usage:
        questions = await search_questions(
            query="What is ATP?",
            subject="Biology",
            top_k=5
        )
    """
    pipeline = get_question_pipeline()
    return await pipeline.search_similar_questions(
        query=query,
        subject=subject,
        topic=topic,
        top_k=top_k
    )
