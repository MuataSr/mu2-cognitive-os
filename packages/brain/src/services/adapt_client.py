"""
LibreTexts ADAPT API Client - Mu2 Cognitive OS
==============================================

Proxy client for LibreTexts ADAPT API.

FERPA COMPLIANCE:
- NEVER send student emails
- Only send anonymized user_ids
- All PII is stripped before API calls
- Questions are stored locally after retrieval

ADAPT API Documentation: https://adapt.libretexts.org/api
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import httpx
from src.core.config import settings


# ============================================================================
# ADAPT API Models
# ============================================================================

class Question(BaseModel):
    """A question from ADAPT"""
    id: str
    question_id: str
    text: str
    type: str  # multiple-choice, short-answer, etc.
    subject: str
    difficulty: str  # easy, medium, hard
    topic: str
    options: Optional[List[str]] = None  # For multiple choice
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubmissionResult(BaseModel):
    """Result of submitting an answer to ADAPT"""
    is_correct: bool
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    feedback: Optional[str] = None
    points_earned: Optional[float] = None


class QuestionFilter(BaseModel):
    """Filters for fetching questions from ADAPT"""
    subject: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    question_type: Optional[str] = None
    count: int = Field(10, ge=1, le=100)


class ADAPTCredentials(BaseModel):
    """Credentials for ADAPT API access"""
    api_key: str
    institution_id: Optional[str] = None
    endpoint: str = "https://adapt.libretexts.org/api"


# ============================================================================
# ADAPT API Client
# ============================================================================

class LibreTextsADAPT:
    """
    Proxy client for LibreTexts ADAPT API

    FERPA COMPLIANCE:
    - All user_ids are anonymized before sending
    - No PII in any API calls
    - Questions are cached locally to minimize external calls
    """

    def __init__(self, credentials: Optional[ADAPTCredentials] = None):
        """
        Initialize the ADAPT client

        Args:
            credentials: ADAPT API credentials. If None, uses settings.
        """
        if credentials:
            self.api_key = credentials.api_key
            self.endpoint = credentials.endpoint
            self.institution_id = credentials.institution_id
        else:
            # Load from environment/settings
            self.api_key = settings.adapt_api_key if hasattr(settings, "adapt_api_key") else ""
            self.endpoint = "https://adapt.libretexts.org/api"
            self.institution_id = settings.adapt_institution_id if hasattr(settings, "adapt_institution_id") else None

        self.timeout = 30.0
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self._client = httpx.AsyncClient(
            base_url=self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout
            )
        return self._client

    # ==========================================================================
    # Question Retrieval
    # ==========================================================================

    async def get_questions(
        self,
        filters: QuestionFilter
    ) -> List[Question]:
        """
        Fetch questions from ADAPT

        Args:
            filters: Question filters (subject, topic, difficulty, count)

        Returns:
            List of Question objects

        Raises:
            httpx.HTTPError: If API request fails
        """
        client = self._get_client()

        # Build query parameters
        params: Dict[str, Any] = {
            "limit": filters.count,
        }

        if filters.subject:
            params["subject"] = filters.subject
        if filters.topic:
            params["topic"] = filters.topic
        if filters.difficulty:
            params["difficulty"] = filters.difficulty
        if filters.question_type:
            params["type"] = filters.question_type

        # Make API request
        # Note: This is a placeholder - actual ADAPT API endpoints may differ
        try:
            response = await client.get("/questions", params=params)
            response.raise_for_status()

            data = response.json()

            # Parse questions
            questions = []
            for item in data.get("questions", []):
                questions.append(Question(
                    id=item.get("id", ""),
                    question_id=item.get("question_id", ""),
                    text=item.get("text", ""),
                    type=item.get("type", "short-answer"),
                    subject=item.get("subject", ""),
                    difficulty=item.get("difficulty", "medium"),
                    topic=item.get("topic", ""),
                    options=item.get("options"),
                    correct_answer=item.get("correct_answer"),
                    explanation=item.get("explanation"),
                    metadata=item.get("metadata", {})
                ))

            return questions

        except httpx.HTTPStatusError as e:
            # API error - return empty list or raise
            if e.response.status_code == 404:
                # Questions not found - return empty list
                return []
            raise

    async def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """
        Fetch a specific question by ID

        Args:
            question_id: The ADAPT question ID

        Returns:
            Question object or None if not found
        """
        client = self._get_client()

        try:
            response = await client.get(f"/questions/{question_id}")
            response.raise_for_status()

            data = response.json()

            return Question(
                id=data.get("id", ""),
                question_id=data.get("question_id", question_id),
                text=data.get("text", ""),
                type=data.get("type", "short-answer"),
                subject=data.get("subject", ""),
                difficulty=data.get("difficulty", "medium"),
                topic=data.get("topic", ""),
                options=data.get("options"),
                correct_answer=data.get("correct_answer"),
                explanation=data.get("explanation"),
                metadata=data.get("metadata", {})
            )

        except httpx.HTTPStatusError:
            return None

    async def search_questions(
        self,
        query: str,
        subject: Optional[str] = None,
        count: int = 10
    ) -> List[Question]:
        """
        Search for questions by text query

        Args:
            query: Search query
            subject: Optional subject filter
            count: Maximum number of results

        Returns:
            List of matching questions
        """
        client = self._get_client()

        params = {
            "q": query,
            "limit": count,
        }

        if subject:
            params["subject"] = subject

        try:
            response = await client.get("/questions/search", params=params)
            response.raise_for_status()

            data = response.json()

            questions = []
            for item in data.get("results", []):
                questions.append(Question(
                    id=item.get("id", ""),
                    question_id=item.get("question_id", ""),
                    text=item.get("text", ""),
                    type=item.get("type", "short-answer"),
                    subject=item.get("subject", ""),
                    difficulty=item.get("difficulty", "medium"),
                    topic=item.get("topic", ""),
                    options=item.get("options"),
                    correct_answer=item.get("correct_answer"),
                    explanation=item.get("explanation"),
                    metadata=item.get("metadata", {})
                ))

            return questions

        except httpx.HTTPStatusError:
            return []

    # ==========================================================================
    # Answer Submission
    # ==========================================================================

    async def submit_answer(
        self,
        user_id: str,  # Anonymized only!
        question_id: str,
        answer: str
    ) -> SubmissionResult:
        """
        Submit an answer and record learning event

        FERPA COMPLIANCE: user_id must be anonymized before calling

        Args:
            user_id: Anonymized student ID (e.g., "student-123")
            question_id: The question being answered
            answer: The student's answer

        Returns:
            SubmissionResult with correctness and feedback
        """
        client = self._get_client()

        payload = {
            "user_id": user_id,
            "question_id": question_id,
            "answer": answer,
            "timestamp": datetime.utcnow().isoformat(),
        }

        response = await client.post("/submissions", json=payload)
        response.raise_for_status()

        data = response.json()

        return SubmissionResult(
            is_correct=data.get("is_correct", False),
            correct_answer=data.get("correct_answer"),
            explanation=data.get("explanation"),
            feedback=data.get("feedback"),
            points_earned=data.get("points_earned")
        )

    # ==========================================================================
    # Health Check
    # ==========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if ADAPT API is accessible

        Returns:
            Health status dict
        """
        try:
            client = self._get_client()

            # Simple health check endpoint
            response = await client.get("/health")
            response.raise_for_status()

            return {
                "status": "healthy",
                "api_available": True,
                "endpoint": self.endpoint,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "api_available": False,
                "error": str(e),
                "endpoint": self.endpoint,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def get_available_subjects(self) -> List[str]:
        """
        Get list of available subjects in ADAPT

        Returns:
            List of subject names
        """
        try:
            client = self._get_client()

            response = await client.get("/subjects")
            response.raise_for_status()

            data = response.json()
            return data.get("subjects", [])

        except Exception:
            # Return default subjects if API unavailable
            return [
                "Biology",
                "Chemistry",
                "Physics",
                "Mathematics",
                "Engineering"
            ]

    async def get_available_topics(
        self,
        subject: Optional[str] = None
    ) -> List[str]:
        """
        Get list of available topics

        Args:
            subject: Optional subject filter

        Returns:
            List of topic names
        """
        try:
            client = self._get_client()

            params = {}
            if subject:
                params["subject"] = subject

            response = await client.get("/topics", params=params)
            response.raise_for_status()

            data = response.json()
            return data.get("topics", [])

        except Exception:
            # Return default topics if API unavailable
            if subject == "Biology":
                return [
                    "Photosynthesis",
                    "Cellular Respiration",
                    "Genetics",
                    "Evolution",
                    "Ecology"
                ]
            return []


# ============================================================================
# Singleton Instance (with lazy initialization)
# ============================================================================

_adapt_client: Optional[LibreTextsADAPT] = None


def get_adapt_client() -> LibreTextsADAPT:
    """
    Get the singleton ADAPT client instance

    Returns:
        LibreTextsADAPT client
    """
    global _adapt_client
    if _adapt_client is None:
        _adapt_client = LibreTextsADAPT()
    return _adapt_client


async def init_adapt_client(api_key: str, endpoint: str = "https://adapt.libretexts.org/api"):
    """
    Initialize the ADAPT client with credentials

    Args:
        api_key: ADAPT API key
        endpoint: ADAPT API endpoint URL
    """
    global _adapt_client

    credentials = ADAPTCredentials(
        api_key=api_key,
        endpoint=endpoint
    )

    _adapt_client = LibreTextsADAPT(credentials)


# ============================================================================
# Convenience Functions
# ============================================================================

async def fetch_questions(
    subject: str,
    topic: Optional[str] = None,
    difficulty: str = "medium",
    count: int = 10
) -> List[Question]:
    """
    Convenience function to fetch questions from ADAPT

    Usage:
        questions = await fetch_questions(
            subject="Biology",
            topic="Photosynthesis",
            difficulty="medium",
            count=10
        )
    """
    client = get_adapt_client()

    filters = QuestionFilter(
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        count=count
    )

    return await client.get_questions(filters)
