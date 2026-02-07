"""
OpenTDB API Client - Mu2 Cognitive OS
====================================

Free, no-API-key alternative to LibreTexts ADAPT.

OpenTDB provides:
- Free JSON API (no registration required)
- Science & Nature category (Category 17)
- General Knowledge, Mathematics, and more
- Creative Commons Attribution-ShareAlike 4.0 license

API Documentation: https://opentdb.com/api_config.php
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import httpx


# ============================================================================
# OpenTDB Models
# ============================================================================

class OpenTDBQuestion(BaseModel):
    """A question from OpenTDB"""
    id: str
    question: str
    correct_answer: str
    incorrect_answers: List[str]
    type: str  # multiple, boolean
    difficulty: str  # easy, medium, hard
    category: str
    category_id: int
    tags: List[str] = Field(default_factory=list)
    source: str = "opentdb"


class OpenTDBResponse(BaseModel):
    """Response from OpenTDB API"""
    response_code: int
    results: List[OpenTDBQuestion]


class OpenTDBCategories(BaseModel):
    """Categories available in OpenTDB"""
    id: int
    name: str


# ============================================================================
# OpenTDB Category IDs
# ============================================================================

# Common OpenTDB Categories (IDs may change)
OPENTDB_CATEGORIES = {
    9: "General Knowledge",
    10: "Entertainment: Books",
    11: "Entertainment: Film",
    12: "Entertainment: Music",
    13: "Entertainment: Musicals & Theatres",
    14: "Entertainment: Television",
    15: "Entertainment: Video Games",
    16: "Entertainment: Board Games",
    17: "Science & Nature",  # <-- Main science category
    18: "Science: Computers",
    19: "Science: Mathematics",
    20: "Mythology",
    21: "Sports",
    22: "Geography",
    23: "History",
    24: "Politics",
    25: "Art",
    26: "Celebrities",
    27: "Animals",
    28: "Vehicles",
    29: "Entertainment: Comics",
    30: "Science: Gadgets",
    31: "Anime & Manga",
    32: "Cartoon & Animations",
    # ... more categories available
}

# Science-related categories
SCIENCE_CATEGORIES = {
    17: "Science & Nature",
    18: "Science: Computers",
    19: "Science: Mathematics",
    27: "Animals",
    30: "Science: Gadgets",
}


# ============================================================================
# OpenTDB API Client
# ============================================================================

class OpenTDBClient:
    """
    Client for OpenTDB API (Free, no API key required)

    Base URL: https://opentdb.com/
    Documentation: https://opentdb.com/api_config.php

    Features:
    - No API key required
    - Free to use
    - Rate limited to 1 request per 5 seconds per IP
    - Maximum 50 questions per request
    """

    BASE_URL = "https://opentdb.com/api.php"

    # Response codes from OpenTDB
    RESPONSE_CODES = {
        0: "Success",
        1: "No Results",
        2: "Invalid Parameter",
        3: "Token Not Found",
        4: "Token Empty",
        5: "Rate Limit",
    }

    def __init__(self):
        """Initialize the OpenTDB client"""
        self.timeout = 30.0
        self._session_token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def get_questions(
        self,
        amount: int = 10,
        category: Optional[int] = None,
        difficulty: Optional[str] = None,
        type: Optional[str] = None
    ) -> List[OpenTDBQuestion]:
        """
        Fetch questions from OpenTDB

        Args:
            amount: Number of questions (1-50)
            category: Category ID (see SCIENCE_CATEGORIES)
            difficulty: "easy", "medium", or "hard"
            type: "multiple" or "boolean"

        Returns:
            List of OpenTDBQuestion objects

        Raises:
            httpx.HTTPError: If API request fails
        """
        client = self._get_client()

        # Build query parameters
        params = {
            "amount": min(amount, 50),  # Max 50 per API limit
        }

        if category is not None:
            params["category"] = category
        if difficulty:
            params["difficulty"] = difficulty
        if type:
            params["type"] = type

        # Add session token if available
        if self._session_token:
            params["token"] = self._session_token

        # Make request
        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()

        # Check response code
        response_code = data.get("response_code", 0)

        if response_code != 0:
            error_msg = self.RESPONSE_CODES.get(response_code, "Unknown error")
            raise Exception(f"OpenTDB error ({response_code}): {error_msg}")

        # Parse results
        questions = []
        for item in data.get("results", []):
            # Map to our format
            question = OpenTDBQuestion(
                id=f"opentdb_{item.get('question_id', '')}",
                question=item.get("question", ""),
                correct_answer=item.get("correct_answer", ""),
                incorrect_answers=item.get("incorrect_answers", []),
                type=item.get("type", ""),
                difficulty=item.get("difficulty", "medium"),
                category=item.get("category", ""),
                category_id=item.get("category", "").split(":")[0].strip(),
                tags=[item.get("category", "")],
                source="opentdb"
            )
            questions.append(question)

        return questions

    async def get_science_questions(
        self,
        amount: int = 10,
        difficulty: Optional[str] = None,
        include_math: bool = True
    ) -> List[OpenTDBQuestion]:
        """
        Get science-related questions from OpenTDB

        This fetches from:
        - Science & Nature (Category 17)
        - Science: Mathematics (Category 19) - if include_math=True
        - Science: Computers (Category 18)
        - Animals (Category 27)

        Args:
            amount: Number of questions per category
            difficulty: Optional difficulty filter
            include_math: Whether to include math questions

        Returns:
            List of science questions
        """
        all_questions = []

        # Science categories to fetch from
        science_cats = [17, 18, 27]  # Nature, Computers, Animals
        if include_math:
            science_cats.append(19)  # Mathematics

        # Fetch from each category
        per_category = max(1, amount // len(science_cats))

        for cat_id in science_cats:
            try:
                questions = await self.get_questions(
                    amount=per_category,
                    category=cat_id,
                    difficulty=difficulty
                )
                all_questions.extend(questions)
            except Exception as e:
                # Log but continue with other categories
                print(f"Warning: Could not fetch from category {cat_id}: {e}")
                continue

        return all_questions

    async def get_categories(self) -> List[OpenTDBCategories]:
        """
        Get list of all available categories

        Returns:
            List of category objects
        """
        client = self._get_client()

        # Use the category endpoint
        response = await client.get("https://opentdb.com/api_category.php")
        response.raise_for_status()

        data = response.json()

        categories = []
        for item in data.get("trivia_categories", []):
            categories.append(OpenTDBCategories(
                id=item.get("id", 0),
                name=item.get("name", "")
            ))

        return categories

    async def get_question_count(self, category: Optional[int] = None) -> int:
        """
        Get count of questions in a category

        Args:
            category: Category ID (None for all questions)

        Returns:
            Number of questions
        """
        client = self._get_client()

        params = {}
        if category:
            params["category"] = category

        response = await client.get("https://opentdb.com/api_count.php", params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("overall", {}).get("total_num_of_questions", 0)

    async def reset_token(self) -> str:
        """
        Reset the session token

        Returns:
            New session token
        """
        client = self._get_client()

        params = {"command": "reset"}

        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()
        self._session_token = data.get("token")

        return self._session_token

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if OpenTDB API is accessible

        Returns:
            Health status dict
        """
        try:
            # Try to fetch a single question
            questions = await self.get_questions(amount=1)

            return {
                "status": "healthy",
                "api_available": True,
                "endpoint": self.BASE_URL,
                "requires_api_key": False,
                "rate_limit": "1 request per 5 seconds",
                "max_questions_per_request": 50,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_available": False,
                "error": str(e),
                "endpoint": self.BASE_URL,
                "timestamp": datetime.utcnow().isoformat()
            }


# ============================================================================
# Convenience Functions
# ============================================================================

async def fetch_science_questions(
    amount: int = 20,
    difficulty: str = "medium"
) -> List[OpenTDBQuestion]:
    """
    Convenience function to fetch science questions from OpenTDB

    Usage:
        questions = await fetch_science_questions(amount=20, difficulty="medium")
    """
    client = OpenTDBClient()
    async with client:
        return await client.get_science_questions(
            amount=amount,
            difficulty=difficulty
        )


async def get_available_categories() -> List[OpenTDBCategories]:
    """
    Get all available OpenTDB categories

    Usage:
        categories = await get_available_categories()
        for cat in categories:
            print(f"{cat.id}: {cat.name}")
    """
    client = OpenTDBClient()
    async with client:
        return await client.get_categories()


# ============================================================================
# Export singleton
# ============================================================================

_opentdb_client: Optional[OpenTDBClient] = None


def get_opentdb_client() -> OpenTDBClient:
    """Get the singleton OpenTDB client instance"""
    global _opentdb_client
    if _opentdb_client is None:
        _opentdb_client = OpenTDBClient()
    return _opentdb_client
