"""
National Science Bowl Importer - Mu2 Cognitive OS
=================================================

Imports National Science Bowl questions from GitHub into Supabase.

National Science Bowl Questions:
- 7,000+ official competition questions
- Middle School and High School levels
- All science categories (Biology, Chemistry, Physics, Earth Science, Math, Energy)
- Source: https://github.com/arxenix/Scibowl_Questions
- Public domain (US government competition questions)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import asyncio
import httpx
import json
import re

from src.services.supabase_vector_store import Question, get_supabase_vector_store

logger = logging.getLogger(__name__)


# ============================================================================
# Import Models
# ============================================================================

class ScienceBowlQuestion(BaseModel):
    """Parsed Science Bowl question"""
    question_text: str
    correct_answer: str
    subject: str
    category: Optional[str] = None
    difficulty: str = "medium"
    question_type: str = "short_answer"
    level: str = "high_school"  # 'middle_school' or 'high_school'
    round_number: Optional[int] = None
    question_number: Optional[int] = None


class ScienceBowlImportResult(BaseModel):
    """Result of Science Bowl import"""
    total_fetched: int
    successfully_imported: int
    failed: int
    errors: List[str] = Field(default_factory=list)
    imported_ids: List[str] = Field(default_factory=list)
    duration_seconds: float


# ============================================================================
# Category Mapping
# ============================================================================

# Standardize category names
CATEGORY_MAPPING = {
    "BIO": "Biology",
    "CHEM": "Chemistry",
    "PHYS": "Physics",
    "ES": "Earth Science",
    "MATH": "Mathematics",
    "ASTR": "Astronomy",
    "ENERGY": "Energy",
    "GENERAL": "General Science",
    "CS": "Computer Science",
    "EARTH": "Earth Science",
    "SPACE": "Astronomy",
}

SHORT_FORM_TO_CATEGORY = {
    "Bio": "Biology",
    "Chem": "Chemistry",
    "Phys": "Physics",
    "Earth": "Earth Science",
    "Math": "Mathematics",
    "Astro": "Astronomy",
    "Energy": "Energy",
    "Gen": "General Science",
}


# ============================================================================
# Science Bowl Importer
# ============================================================================

class ScienceBowlImporter:
    """
    Import National Science Bowl questions from GitHub into Supabase

    Downloads from GitHub repository and stores with embeddings.
    """

    GITHUB_RAW_URL = "https://raw.githubusercontent.com/arxenix/Scibowl_Questions/master"
    GITHUB_API_URL = "https://api.github.com/repos/arxenix/Scibowl_Questions/contents"

    def __init__(self, batch_size: int = 50):
        """
        Initialize the Science Bowl importer

        Args:
            batch_size: Number of questions to process per batch
        """
        self.batch_size = batch_size

    async def fetch_dataset(self) -> List[ScienceBowlQuestion]:
        """
        Fetch Science Bowl questions from GitHub

        Returns:
            List of Science Bowl questions
        """
        logger.info("Fetching Science Bowl questions from GitHub...")

        all_questions = []

        try:
            # Fetch repository contents
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                # First, try to get the root-level questions.json file
                response = await client.get(f"{self.GITHUB_API_URL}/questions.json")
                if response.status_code == 200:
                    logger.info("Found root-level questions.json file")
                    all_questions = await self._fetch_root_questions(client)
                else:
                    # Fallback: Try to get high/middle school subdirectories
                    hs_questions = await self._fetch_high_school_questions(client)
                    all_questions.extend(hs_questions)

                    ms_questions = await self._fetch_middle_school_questions(client)
                    all_questions.extend(ms_questions)

            logger.info(f"Fetched {len(all_questions)} total questions from GitHub")
            return all_questions

        except Exception as e:
            logger.error(f"Error fetching dataset: {e}")
            return []

    async def _fetch_high_school_questions(self, client: httpx.AsyncClient) -> List[ScienceBowlQuestion]:
        """Fetch high school science bowl questions"""
        questions = []

        try:
            # Try to get list of files in the repository
            response = await client.get(
                f"{self.GITHUB_API_URL}/High%20School"
            )
            response.raise_for_status()
            files = response.json()

            for file in files:
                if file.get("type") == "file" and file.get("name", "").endswith(".json"):
                    # Download and parse JSON file
                    file_url = file.get("download_url")
                    if file_url:
                        file_questions = await self._fetch_json_file(client, file_url, "high_school")
                        questions.extend(file_questions)

        except Exception as e:
            logger.warning(f"Could not fetch high school questions: {e}")
            # Try fallback URLs
            questions = await self._fetch_fallback_high_school(client)

        return questions

    async def _fetch_middle_school_questions(self, client: httpx.AsyncClient) -> List[ScienceBowlQuestion]:
        """Fetch middle school science bowl questions"""
        questions = []

        try:
            response = await client.get(
                f"{self.GITHUB_API_URL}/Middle%20School"
            )
            response.raise_for_status()
            files = response.json()

            for file in files:
                if file.get("type") == "file" and file.get("name", "").endswith(".json"):
                    file_url = file.get("download_url")
                    if file_url:
                        file_questions = await self._fetch_json_file(client, file_url, "middle_school")
                        questions.extend(file_questions)

        except Exception as e:
            logger.warning(f"Could not fetch middle school questions: {e}")

        return questions

    async def _fetch_root_questions(self, client: httpx.AsyncClient) -> List[ScienceBowlQuestion]:
        """
        Fetch questions from the root-level questions.json file

        Note: The Science Bowl dataset stores questions as image files,
        not text. This method provides a best-effort extraction but may
        not yield usable questions without OCR.
        """
        questions = []

        try:
            url = f"{self.GITHUB_RAW_URL}/questions.json"
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            # The Science Bowl dataset has questions stored as images
            # with metadata in JSON. We can't easily import without OCR.
            logger.warning(
                "Science Bowl dataset questions are stored as images, not text. "
                "This dataset requires OCR for text extraction and is not "
                "directly compatible with the text-based question system."
            )

            # Try to extract what we can from the metadata
            if "questions" in data:
                for item in data["questions"][:10]:  # Limit to 10 for testing
                    # Check if there's a text field (unlikely)
                    if "question" in item and isinstance(item["question"], str):
                        parsed = self._parse_json_question(item, "high_school")
                        if parsed:
                            questions.append(parsed)
                    else:
                        logger.debug(
                            f"Skipping question {item.get('num', '?')}: "
                            f"No text field found (image-based question)"
                        )

            logger.info(f"Extracted {len(questions)} text-based questions from Science Bowl dataset")
            return questions

        except Exception as e:
            logger.warning(f"Could not fetch root questions file: {e}")
            return []

    async def _fetch_json_file(
        self,
        client: httpx.AsyncClient,
        url: str,
        level: str
    ) -> List[ScienceBowlQuestion]:
        """Fetch and parse a JSON question file"""
        questions = []

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            # Parse based on structure
            if isinstance(data, list):
                for item in data:
                    parsed = self._parse_json_question(item, level)
                    if parsed:
                        questions.append(parsed)
            elif isinstance(data, dict):
                # Check for 'questions' key
                if "questions" in data:
                    for item in data["questions"]:
                        parsed = self._parse_json_question(item, level)
                        if parsed:
                            questions.append(parsed)
                else:
                    # Single question
                    parsed = self._parse_json_question(data, level)
                    if parsed:
                        questions.append(parsed)

        except Exception as e:
            logger.warning(f"Error parsing JSON file {url}: {e}")

        return questions

    def _parse_json_question(
        self,
        data: Dict[str, Any],
        level: str
    ) -> Optional[ScienceBowlQuestion]:
        """Parse a single question from JSON data"""
        try:
            # Extract question text
            question_text = data.get("question") or data.get("text", "")
            if not question_text:
                return None

            # Extract answer
            correct_answer = data.get("answer") or data.get("correct_answer", "")
            if not correct_answer:
                return None

            # Extract category/subject
            category = data.get("category") or data.get("subject", "")
            subject = self._standardize_subject(category)

            # Determine difficulty based on level
            difficulty = "easy" if level == "middle_school" else "medium"

            return ScienceBowlQuestion(
                question_text=question_text,
                correct_answer=correct_answer,
                subject=subject,
                category=category,
                difficulty=difficulty,
                level=level,
                question_type="short_answer",
                round_number=data.get("round"),
                question_number=data.get("number")
            )

        except Exception as e:
            logger.warning(f"Error parsing question: {e}")
            return None

    def _standardize_subject(self, category: str) -> str:
        """Standardize subject/category name"""
        if not category:
            return "General Science"

        category_upper = category.upper().strip()

        # Check direct mapping
        if category_upper in CATEGORY_MAPPING:
            return CATEGORY_MAPPING[category_upper]

        # Check for substring matches
        for key, value in CATEGORY_MAPPING.items():
            if key in category_upper:
                return value

        # Check short form mapping
        for key, value in SHORT_FORM_TO_CATEGORY.items():
            if key.lower() in category.lower():
                return value

        return "General Science"

    async def _fetch_fallback_high_school(self, client: httpx.AsyncClient) -> List[ScienceBowlQuestion]:
        """Fallback method to fetch questions using raw URLs"""
        questions = []

        # List of round files to try
        round_files = [
            "round1.json",
            "round2.json",
            "round3.json",
            "round4.json",
            "round5.json",
        ]

        for round_file in round_files:
            try:
                url = f"{self.GITHUB_RAW_URL}/High%20School/{round_file}"
                file_questions = await self._fetch_json_file(client, url, "high_school")
                questions.extend(file_questions)
            except Exception as e:
                logger.debug(f"Could not fetch {round_file}: {e}")
                continue

        return questions

    async def import_dataset(
        self,
        max_questions: Optional[int] = None,
        subjects: Optional[List[str]] = None,
        level: Optional[str] = None
    ) -> ScienceBowlImportResult:
        """
        Import Science Bowl questions into Supabase

        Args:
            max_questions: Maximum number of questions to import (None for all)
            subjects: Filter by subjects (None for all)
            level: Filter by level ('middle_school', 'high_school', None for both)

        Returns:
            Import result with statistics
        """
        start_time = datetime.utcnow()
        errors = []
        imported_ids = []
        success_count = 0
        failed_count = 0

        try:
            # Fetch dataset
            sb_questions = await self.fetch_dataset()

            # Apply filters
            if subjects:
                sb_questions = [q for q in sb_questions if q.subject in subjects]

            if level:
                sb_questions = [q for q in sb_questions if q.level == level]

            if max_questions:
                sb_questions = sb_questions[:max_questions]

            total_fetched = len(sb_questions)

            if total_fetched == 0:
                return ScienceBowlImportResult(
                    total_fetched=0,
                    successfully_imported=0,
                    failed=0,
                    errors=["No questions fetched from Science Bowl dataset"],
                    duration_seconds=(datetime.utcnow() - start_time).total_seconds()
                )

            logger.info(f"Importing {total_fetched} Science Bowl questions")

            # Get vector store
            vector_store = get_supabase_vector_store()

            # Process in batches
            for i in range(0, len(sb_questions), self.batch_size):
                batch = sb_questions[i:i + self.batch_size]
                batch_questions = []

                for idx, sb_q in enumerate(batch):
                    try:
                        # Infer topic from question content
                        topic = self._infer_topic(sb_q)

                        # Create Question object
                        question = Question(
                            question_id=f"science_bowl_{i + idx}",
                            question_text=sb_q.question_text,
                            question_type=sb_q.question_type,
                            subject=sb_q.subject,
                            topic=topic,
                            difficulty=sb_q.difficulty,
                            grade_level=9 if sb_q.level == "high_school" else 6,
                            correct_answer=sb_q.correct_answer,
                            incorrect_answers=[],
                            explanation=None,
                            source="science_bowl",
                            metadata={
                                "level": sb_q.level,
                                "category": sb_q.category,
                                "round_number": sb_q.round_number,
                                "question_number": sb_q.question_number,
                                "dataset": "National Science Bowl"
                            }
                        )
                        batch_questions.append(question)

                    except Exception as e:
                        logger.error(f"Error processing question {i + idx}: {e}")
                        errors.append(f"{i + idx}: {str(e)}")
                        failed_count += 1
                        continue

                # Add batch to vector store
                if batch_questions:
                    result = await vector_store.add_questions_batch(batch_questions)
                    success_count += result["success"]
                    failed_count += result["failed"]
                    errors.extend(result["errors"])
                    imported_ids.extend([q.question_id for q in batch_questions[:result["success"]]])

                logger.info(f"Processed batch {i // self.batch_size + 1}: {success_count}/{total_fetched}")

            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"Science Bowl import complete: {success_count}/{total_fetched} questions "
                f"imported in {duration:.2f}s"
            )

            return ScienceBowlImportResult(
                total_fetched=total_fetched,
                successfully_imported=success_count,
                failed=failed_count,
                errors=errors,
                imported_ids=imported_ids,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Error importing Science Bowl dataset: {e}")
            return ScienceBowlImportResult(
                total_fetched=0,
                successfully_imported=0,
                failed=0,
                errors=[str(e)],
                duration_seconds=(datetime.utcnow() - start_time).total_seconds()
            )

    def _infer_topic(self, question: ScienceBowlQuestion) -> Optional[str]:
        """
        Infer topic from question content

        Args:
            question: Science Bowl question

        Returns:
            Topic name or None
        """
        question_lower = question.question_text.lower()

        # Common topics mapping
        topic_keywords = {
            "Photosynthesis": ["photosynthesis", "chlorophyll", "chloroplast"],
            "Cellular Respiration": ["respiration", "glucose", "atp", "cellular respiration"],
            "Genetics": ["gene", "genetic", "inherit", "trait", "dna", "chromosome"],
            "Evolution": ["evolution", "natural selection", "adaptation", "species"],
            "Ecology": ["ecosystem", "habitat", "environment", "population", "community"],
            "Atomic Structure": ["atom", "electron", "proton", "neutron", "nucleus", "orbital"],
            "Periodic Table": ["periodic", "element", "group", "period", "atomic number"],
            "Chemical Bonding": ["bond", "ionic", "covalent", "molecule", "valence"],
            "Acids and Bases": ["acid", "base", "ph", "neutralize", "titration"],
            "Stoichiometry": ["mole", "stoichiometry", "molar mass", "limiting reactant"],
            "Newton's Laws": ["newton", "force", "motion", "inertia", "acceleration"],
            "Energy and Work": ["energy", "kinetic", "potential", "work", "power", "joule"],
            "Waves and Sound": ["wave", "frequency", "amplitude", "wavelength", "sound"],
            "Light and Optics": ["light", "optic", "lens", "mirror", "reflection", "refraction"],
            "Electricity": ["electric", "current", "voltage", "circuit", "ohm", "resistor"],
            "Magnetism": ["magnet", "magnetic", "pole", "field", "flux"],
            "Thermodynamics": ["heat", "temperature", "entropy", "enthalpy", "thermodynamics"],
            "Earth Science": ["earth", "geology", "rock", "mineral", "plate tectonics", "fault"],
            "Astronomy": ["star", "planet", "orbit", "solar system", "galaxy", "telescope"],
            "Weather": ["weather", "climate", "precipitation", "atmosphere", "front"],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in question_lower for kw in keywords):
                return topic

        return None


# ============================================================================
# Singleton Instance
# ============================================================================

_science_bowl_importer: Optional[ScienceBowlImporter] = None


def get_science_bowl_importer() -> ScienceBowlImporter:
    """Get the singleton Science Bowl importer instance"""
    global _science_bowl_importer
    if _science_bowl_importer is None:
        _science_bowl_importer = ScienceBowlImporter()
    return _science_bowl_importer


# ============================================================================
# Convenience Functions
# ============================================================================

async def import_science_bowl_questions(
    max_questions: Optional[int] = None,
    subjects: Optional[List[str]] = None,
    level: Optional[str] = None
) -> ScienceBowlImportResult:
    """
    Import National Science Bowl questions into Supabase

    Usage:
        # Import all questions
        result = await import_science_bowl_questions()

        # Import only Physics questions
        result = await import_science_bowl_questions(subjects=["Physics"])

        # Import high school questions only
        result = await import_science_bowl_questions(level="high_school")

        # Import first 100 questions
        result = await import_science_bowl_questions(max_questions=100)

        print(f"Imported {result.successfully_imported} questions")
    """
    importer = get_science_bowl_importer()
    return await importer.import_dataset(
        max_questions=max_questions,
        subjects=subjects,
        level=level
    )
