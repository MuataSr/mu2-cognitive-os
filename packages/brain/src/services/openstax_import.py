"""
OpenStax Instructor Test Bank Import - Mu2 Cognitive OS
====================================================

Imports questions from OpenStax Instructor Test Banks.

OpenStax provides instructor resources including test banks that can be
downloaded and imported locally (no API key required).

This approach:
- Downloads test bank PDFs from OpenStax instructor resources
- Parses questions from PDF content
- Imports into local vector store
- FERPA compliant (all local processing)

Question Sources:
- OpenStax Biology 2e Instructor Test Bank
- Anatomy & Physiology Test Banks
- Chemistry of Life Test Banks
- Future: Other OpenStax test banks

FERPA Compliance:
- All questions stored locally in Supabase/Postgres
- No PII in question data
- Downloaded once, used offline
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
import httpx

from src.core.config import settings, OPENSTAX_DATA_DIR


class OpenStaxQuestion(BaseModel):
    """Question from OpenStax test bank"""
    id: str = Field(..., description="Unique question identifier")
    type: str = Field(..., description="Question type")
    subject: str = Field(..., description="Subject area")
    stem: str = Field(..., description="Question text")
    options: Optional[List[str]] = Field(None, description="Answer choices (if multiple choice)")
    correct_answer: str = Field(..., description="Correct answer")
    explanation: Optional[str] = Field(None, description="Explanation")
    chapter_ref: Optional[str] = Field(None, description="Chapter reference")
    section_ref: Optional[str] = Field(None, description="Section reference")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional data")


class ImportProgress(BaseModel):
    """Progress of import operation"""
    total_questions: int = Field(..., description="Total questions to process")
    processed: int = Field(0, description="Questions processed so far")
    successful: int = Field(0, description="Questions successfully imported")
    failed: int = Field(0, description="Questions that failed to import")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    source_file: str = Field(..., description="Source file name")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Start time")
    duration_seconds: Optional[float] = Field(None, description="Duration in seconds")


class OpenStaxImporter:
    """
    Import OpenStax Instructor Test Bank questions

    This is the main service for Phase D (Question Bank Integration).
    """

    def __init__(self):
        """Initialize the importer"""
        self.storage_dir = OPENSTAX_DATA_DIR / "test_banks"
        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # HTTP client for downloads (with timeout)
        self.client = httpx.AsyncClient(timeout=30.0)

        # Statistics
        self._stats = {
            "total_imported": 0,
            "by_source": {},
            "by_subject": {},
        }

    def _get_test_bank_url(self, subject: str) -> str:
        """
        Get the URL for OpenStax instructor test bank

        Args:
            subject: Subject area (e.g., 'biology-2e')

        Returns:
            Full URL to test bank
        """
        base_url = settings.openstax_instructor_base

        # Map subjects to OpenStax resource names
        subject_map = {
            "biology-2e": "biology-2e",
            "anatomy-physiology": "anatomy-physiology",
            "chemistry": "chemistry-misc",  # Chemistry of Life
        }

        subject_slug = subject_map.get(subject, subject)

        return f"{base_url}/details/{subject_slug}/instructor"

    def _get_pdf_urls(self, subject: str) -> List[str]:
        """
        Get direct PDF URLs for test banks

        Note: This bypasses the need for scraping by directly accessing
        known PDF patterns. In production, we'd need to
        scrape the instructor resources page.

        Args:
            subject: Subject area

        Returns:
            List of PDF URLs to try
        """
        # Common PDF URL patterns for OpenStax test banks
        # These would need to be discovered or maintained
        pdf_patterns = [
            f"{settings.openstax_instructor_base}/{subject}/instructor/resources",
            f"{settings.openstax_instructor_base}/books/{subject}/instructor",
            "https://openstax.org/contents/biology-2e",  # Direct to book
        ]

        # For now, return book page (which links to instructor resources)
        return [pdf_patterns[0]]

    async def download_test_bank_pdf(self, subject: str) -> Optional[bytes]:
        """
        Download test bank PDF from OpenStax

        Args:
            subject: Subject area

        Returns:
            PDF content or None if failed
        """
        urls = self._get_pdf_urls(subject)

        for url in urls:
            try:
                response = await self.client.get(url)
                if response.status_code == 200:
                    # Check if we got a PDF
                    content_type = response.headers.get("content-type", "")

                    if "application/pdf" in content_type or "pdf" in url.lower():
                        return response.content
                    else:
                        # Try to find PDF link in HTML
                        # This would require HTML parsing (BeautifulSoup)
                        pass
            except Exception as e:
                print(f"Download failed for {url}: {e}")
                continue

        return None

    def _parse_pdf_questions(self, pdf_content: bytes, subject: str) -> List[OpenStaxQuestion]:
        """
        Parse questions from PDF content

        This is a placeholder - actual implementation would require:
        - PyPDF2 or pdfplumber for PDF parsing
        - Question extraction logic
        - Answer key parsing

        For Phase D, we'll implement JSON-based import instead.

        Args:
            pdf_content: PDF file content
            subject: Subject area

        Returns:
            List of parsed questions
        """
        # TODO: Implement PDF parsing
        # For now, return empty list
        return []

    async def import_from_json(self, json_file: Path, subject: str) -> ImportProgress:
        """
        Import questions from JSON file

        JSON files can be manually created from OpenStax instructor resources
        by copying questions and saving as JSON.

        Args:
            json_file: Path to JSON file
            subject: Subject area

        Returns:
            Import progress
        """
        progress = ImportProgress(
            total_questions=0,
            source_file=json_file.name,
            started_at=datetime.utcnow()
        )

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                questions = data.get("questions", [])
                progress.total_questions = len(questions)

                # Import each question
                for q_data in questions:
                    try:
                        question = OpenStaxQuestion(
                            id=q_data.get("id", f"q_{len(self._stats['total_imported']) + 1}"),
                            type=q_data.get("type", "multiple_choice"),
                            subject=subject,
                            stem=q_data.get("question", ""),
                            options=q_data.get("options", []),
                            correct_answer=q_data.get("answer", ""),
                            explanation=q_data.get("explanation"),
                            chapter_ref=q_data.get("chapter"),
                            section_ref=q_data.get("section"),
                            metadata={
                                "source": "openstax-instructor",
                                "imported_at": datetime.utcnow().isoformat()
                            }
                        )

                        # Add to question bank service
                        from src.services.question_bank import question_bank
                        bank = question_bank()
                        await bank.add_question(question.model_dump())

                        progress.successful += 1
                    except Exception as e:
                        progress.failed += 1
                        progress.errors.append(f"Question {q_data.get('id', '?')}: {str(e)}")

                # Update stats
                self._stats["total_imported"] += progress.total_questions
                self._stats["by_source"][progress.source_file] = {
                    "imported": progress.successful,
                    "failed": progress.failed,
                    "total": progress.total_questions
                }

                progress.duration_seconds = (datetime.utcnow() - progress.started_at).total_seconds()

        except Exception as e:
            progress.errors.append(f"File read error: {str(e)}")

        return progress

    async def import_subject_questions(
        self,
        subject: str,
        max_count: Optional[int] = None
    ) -> ImportProgress:
        """
        Import all questions for a subject

        Args:
            subject: Subject to import (e.g., 'biology-2e')
            max_count: Maximum number of questions to import

        Returns:
            Import progress
        """
        # Try JSON files first
        json_dir = self.storage_dir / subject

        if json_dir.exists():
            json_files = list(json_dir.glob("*.json"))

            for json_file in json_files[:5]:  # Process up to 5 JSON files
                progress = await self.import_from_json(json_file, subject)

                if max_count and (self._stats["total_imported"] >= max_count):
                    break

                if progress.successful > 0:
                    return progress

        # If no JSON files, try PDF download
        # pdf_content = await self.download_test_bank_pdf(subject)
        # if pdf_content:
        #     questions = self._parse_pdf_questions(pdf_content, subject)
        #     if questions:
        #         # Add to question bank
        #
        # Return progress even if no questions found
        return ImportProgress(
            total_questions=0,
            source_file=f"{subject}_test_bank",
            started_at=datetime.utcnow()
        )

    async def get_import_statistics(self) -> Dict[str, Any]:
        """
        Get import statistics

        Returns:
            Dictionary with import stats
        """
        return {
            **self._stats,
            "storage_dir": str(self.storage_dir),
        }

    def clear_cache(self) -> None:
        """Clear any cached data"""
        # HTTP client is stateless, no cache to clear
        pass


# Singleton instance
openstax_importer = OpenStaxImporter()
