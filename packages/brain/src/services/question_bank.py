"""
Question Bank Service - Mu2 Cognitive OS
========================================

Manages STEM questions from OpenStax Instructor Resources.

This service:
1. Parses OpenStax test bank PDFs
2. Stores questions in local database
3. Serves questions via API (FERPA compliant)

"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

from datetime import datetime, timedelta


class QuestionType(str, Enum):
    """Types of questions"""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    FILL_BLANK = "fill_blank"
    MATCHING = "matching"


class DifficultyLevel(str, Enum):
    """Difficulty levels for questions"""
    ELEMENTARY = "elementary"
    MIDDLE = "middle"
    HIGH = "high"
    AP = "ap"


class Subject(str, Enum):
    """Subject areas"""
    BIOLOGY = "biology"
    CHEMISTRY = "chemistry"
    PHYSICS = "physics"
    MATH = "math"


class Question(BaseModel):
    """A question from OpenStax test bank"""
    id: str = Field(..., description="Unique question identifier")
    type: QuestionType = Field(..., description="Question type")
    subject: Subject = Field(..., description="Subject area")
    stem: str = Field(..., description="Question stem/prompt")
    difficulty: DifficultyLevel = Field(..., description="Difficulty level")
    options: Optional[List[str]] = Field(None, description="Answer options (for multiple choice)")
    correct_answer: str = Field(..., description="Correct answer")
    explanation: Optional[str] = Field(None, description="Explanation")
    chapter_ref: Optional[str] = Field(None, description="OpenStax chapter reference")
    section_ref: Optional[str] = Field(None, description="OpenStax section reference")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class QuestionBank:
    """
    Question Bank Service for Mu2 Cognitive OS

    Manages STEM questions from OpenStax Instructor Resources.
    FERPA compliant - all data stored locally.
    """

    def __init__(self):
        """Initialize the question bank"""
        self._questions: Dict[str, Question] = {}
        self._indexes = {
            "by_subject": {},
            "by_difficulty": {},
            "by_chapter": {},
        }

    async def add_question(self, question: Question) -> bool:
        """
        Add a single question to the bank

        Args:
            question: Question object to add

        Returns:
            True if added, False if already exists
        """
        if question.id in self._questions:
            return False

        self._questions[question.id] = question

        # Update indexes
        subject = question.subject.value if isinstance(question.subject, Enum) else str(question.subject)
        difficulty = question.difficulty.value if isinstance(question.difficulty, Enum) else str(question.difficulty)

        if subject not in self._indexes["by_subject"]:
            self._indexes["by_subject"][subject] = []
        self._indexes["by_subject"][subject].append(question.id)

        if difficulty not in self._indexes["by_difficulty"]:
            self._indexes["by_difficulty"][difficulty] = []
        self._indexes["by_difficulty"][difficulty].append(question.id)

        if question.chapter_ref:
            chapter = question.chapter_ref
            if chapter not in self._indexes["by_chapter"]:
                self._indexes["by_chapter"][chapter] = []
            self._indexes["by_chapter"][chapter].append(question.id)

        return True

    async def get_question(self, question_id: str) -> Optional[Question]:
        """
        Get a question by ID

        Args:
            question_id: Unique question identifier

        Returns:
            Question object or None if not found
        """
        return self._questions.get(question_id)

    async def get_questions_by_subject(
        self,
        subject: str
    ) -> List[Question]:
        """
        Get all questions for a subject

        Args:
            subject: Subject area (e.g., 'biology')

        Returns:
            List of questions
        """
        question_ids = self._indexes["by_subject"].get(subject, [])
        return [self._questions[qid] for qid in question_ids if qid in self._questions]

    async def get_questions_by_difficulty(
        self,
        difficulty: str
    ) -> List[Question]:
        """
        Get all questions by difficulty level

        Args:
            difficulty: Difficulty level (e.g., 'medium')

        Returns:
            List of questions
        """
        question_ids = self._indexes["by_difficulty"].get(difficulty, [])
        return [self._questions[qid] for qid in question_ids if qid in self._questions]

    async def get_questions_by_chapter(
        self,
        chapter_ref: str
    ) -> List[Question]:
        """
        Get all questions for a chapter

        Args:
            chapter_ref: Chapter reference (e.g., '2.1')

        Returns:
            List of questions
        """
        question_ids = self._indexes["by_chapter"].get(chapter_ref, [])
        return [self._questions[qid] for qid in question_ids if qid in self._questions]

    async def get_random_questions(
        self,
        count: int = 10,
        subject: Optional[str] = None,
        difficulty: Optional[str] = None,
        chapter: Optional[str] = None
    ) -> List[Question]:
        """
        Get random questions

        Args:
            count: Number of questions to return
            subject: Filter by subject
            difficulty: Filter by difficulty
            chapter: Filter by chapter

        Returns:
            List of random questions
        """
        import random

        candidates = list(self._questions.values())

        # Apply filters
        if subject:
            candidates = [q for q in candidates if str(q.subject.value) == subject]
        if difficulty:
            candidates = [q for q in candidates if str(q.difficulty.value) == difficulty]
        if chapter:
            candidates = [q for q in candidates if q.chapter_ref == chapter]

        count = min(count, len(candidates))
        return random.sample(candidates, count) if candidates else []

    async def search_questions(
        self,
        query: str,
        limit: int = 20
    ) -> List[Question]:
        """
        Full-text search for questions

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching questions
        """
        query_lower = query.lower()
        results = []

        for question in self._questions.values():
            # Search in stem
            if query_lower in question.stem.lower():
                results.append(question)
                continue

            # Search in explanation
            if question.explanation and query_lower in question.explanation.lower():
                results.append(question)
                continue

            # Search in chapter/section refs
            if question.chapter_ref and query_lower in question.chapter_ref.lower():
                results.append(question)
                continue

            if len(results) >= limit:
                break

        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get question bank statistics

        Returns:
            Dictionary with statistics
        """
        by_subject = {}
        for subject, ids in self._indexes["by_subject"].items():
            by_subject[subject] = len(ids)

        by_difficulty = {}
        for difficulty, ids in self._indexes["by_difficulty"].items():
            by_difficulty[difficulty] = len(ids)

        return {
            "total_questions": len(self._questions),
            "by_subject": by_subject,
            "by_difficulty": by_difficulty,
            "chapters_covered": len(self._indexes["by_chapter"]),
        }

    def export_to_json(self, file_path: str) -> None:
        """
        Export all questions to JSON file

        Args:
            file_path: Path to output JSON file
        """
        questions_data = {
            "questions": [q.model_dump() for q in self._questions.values()]
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(questions_data, f, indent=2, ensure_ascii=False)

    async def import_from_json(self, file_path: str) -> int:
        """
        Import questions from JSON file

        Args:
            file_path: Path to JSON file

        Returns:
            Number of questions imported
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count = 0
        for q_data in data.get("questions", []):
            try:
                question = Question(**q_data)
                await self.add_question(question)
                count += 1
            except Exception as e:
                print(f"Failed to import question {q_data.get('id', '?')}: {e}")

        return count


# Singleton instance
question_bank = QuestionBank()


async def get_question_bank() -> QuestionBank:
    """Get question bank singleton instance"""
    return question_bank
