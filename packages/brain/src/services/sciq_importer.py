"""
SciQ Dataset Importer - Mu2 Cognitive OS
========================================

Imports the SciQ dataset from HuggingFace into Supabase.

SciQ Dataset:
- 13,679 crowdsourced science exam questions
- Covers Physics, Chemistry, Biology
- Source: https://huggingface.co/datasets/allenai/sciq
- License: Apache 2.0
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import asyncio
import httpx

from src.services.supabase_vector_store import Question, get_supabase_vector_store

logger = logging.getLogger(__name__)


# ============================================================================
# Import Models
# ============================================================================

class SciQQuestion(BaseModel):
    """Raw SciQ question from HuggingFace"""
    question: str
    distractor1: str
    distractor2: str
    distractor3: str
    correct_answer: str
    support: Optional[str] = None  # Supporting evidence


class SciQImportResult(BaseModel):
    """Result of SciQ import"""
    total_fetched: int
    successfully_imported: int
    failed: int
    errors: List[str] = Field(default_factory=list)
    imported_ids: List[str] = Field(default_factory=list)
    duration_seconds: float


# ============================================================================
# SciQ Importer
# ============================================================================

class SciQImporter:
    """
    Import SciQ dataset from HuggingFace into Supabase

    Downloads from HuggingFace datasets API and stores with embeddings.
    """

    HF_API_URL = "https://huggingface.co/api/datasets/allenai/sciq"
    HF_REPO = "allenai/sciq"

    def __init__(self, batch_size: int = 50):
        """
        Initialize the SciQ importer

        Args:
            batch_size: Number of questions to process per batch
        """
        self.batch_size = batch_size

    async def fetch_dataset(self) -> List[SciQQuestion]:
        """
        Fetch the SciQ dataset from HuggingFace

        Returns:
            List of SciQ questions
        """
        logger.info("Fetching SciQ dataset from HuggingFace...")

        try:
            # Try to fetch from HuggingFace files API
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                # Get dataset info
                response = await client.get(self.HF_API_URL)
                response.raise_for_status()
                data = response.json()

                # Get the default split file URL
                # SciQ has 'train', 'validation', and 'test' splits
                repo_id = data.get("id", self.HF_REPO)
                splits = data.get("cardData", {}).get("splits", ["train", "validation", "test"])

                all_questions = []

                # Download each split
                for split in splits:
                    try:
                        # Use the correct file pattern: {split}-00000-of-00001.parquet
                        url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/data/{split}-00000-of-00001.parquet"
                        logger.info(f"Downloading {split} split from {url}...")

                        # Try parquet format
                        response = await client.get(url)
                        if response.status_code == 200:
                            import io

                            # Use pyarrow to read parquet
                            import pyarrow.parquet as pq
                            import pyarrow as pa

                            parquet_file = pq.read_table(io.BytesIO(response.content))
                            df = parquet_file.to_pydict()

                            # Convert to SciQ questions
                            for i in range(len(df["question"])):
                                all_questions.append(SciQQuestion(
                                    question=df["question"][i],
                                    distractor1=df["distractor1"][i] if "distractor1" in df else "",
                                    distractor2=df["distractor2"][i] if "distractor2" in df else "",
                                    distractor3=df["distractor3"][i] if "distractor3" in df else "",
                                    correct_answer=df["correct_answer"][i],
                                    support=df.get("support", [None] * len(df["question"]))[i] if "support" in df else None
                                ))

                            logger.info(f"Downloaded {len(df['question'])} questions from {split} split")

                    except Exception as e:
                        logger.warning(f"Could not download {split} split: {e}")
                        continue

                if not all_questions:
                    # Fallback: Try to fetch raw JSON from HF hub
                    logger.info("Trying fallback method...")
                    all_questions = await self._fetch_fallback(client)

                return all_questions

        except Exception as e:
            logger.error(f"Error fetching dataset: {e}")
            # Try fallback method
            return await self._fetch_fallback()

    async def _fetch_fallback(self, client: Optional[httpx.AsyncClient] = None) -> List[SciQQuestion]:
        """
        Fallback method to fetch SciQ dataset

        Uses direct raw file download
        """
        should_close = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

        try:
            # Download raw train split
            url = "https://huggingface.co/datasets/allenai/sciq/resolve/main/train/train.jsonl"
            response = await client.get(url)

            if response.status_code == 200:
                import json

                questions = []
                for line in response.text.split("\n"):
                    if line.strip():
                        data = json.loads(line)
                        questions.append(SciQQuestion(**data))

                logger.info(f"Fetched {len(questions)} questions from fallback URL")
                return questions

        except Exception as e:
            logger.warning(f"Fallback fetch failed: {e}")

        finally:
            if should_close:
                await client.aclose()

        return []

    def _classify_subject(self, question: SciQQuestion) -> str:
        """
        Classify question into subject area

        Args:
            question: SciQ question

        Returns:
            Subject category
        """
        question_lower = question.question.lower()

        # Biology keywords
        bio_keywords = [
            "cell", "organism", "plant", "animal", "gene", "protein",
            "photosynthesis", "respiration", "dna", "mitosis", "meiosis",
            "ecosystem", "species", "evolution", "bacteria", "virus",
            "tissue", "organ", "blood", "heart", "brain", "muscle"
        ]

        # Chemistry keywords
        chem_keywords = [
            "atom", "molecule", "element", "compound", "reaction",
            "chemical", "bond", "acid", "base", "solution", "mixture",
            "periodic", "electron", "proton", "neutron", "ion", "ph",
            "oxidation", "reduction", "catalyst", "polymer"
        ]

        # Physics keywords
        physics_keywords = [
            "force", "energy", "velocity", "acceleration", "mass",
            "gravity", "friction", "momentum", "wave", "light", "sound",
            "electric", "magnetic", "circuit", "voltage", "current",
            "heat", "temperature", "pressure", "motion", "power"
        ]

        # Count keyword matches
        bio_count = sum(1 for kw in bio_keywords if kw in question_lower)
        chem_count = sum(1 for kw in chem_keywords if kw in question_lower)
        physics_count = sum(1 for kw in physics_keywords if kw in question_lower)

        # Return subject with most matches
        if bio_count >= chem_count and bio_count >= physics_count:
            return "Biology"
        elif chem_count >= physics_count:
            return "Chemistry"
        else:
            return "Physics"

    def _infer_topic(self, question: SciQQuestion) -> Optional[str]:
        """
        Infer topic from question content

        Args:
            question: SciQ question

        Returns:
            Topic name or None
        """
        question_lower = question.question.lower()

        # Common topics mapping
        topic_keywords = {
            "Photosynthesis": ["photosynthesis", "chlorophyll", "chloroplast"],
            "Cellular Respiration": ["respiration", "glucose", "atp"],
            "Genetics": ["gene", "genetic", "inherit", "trait", "dna"],
            "Evolution": ["evolution", "natural selection", "adaptation", "species"],
            "Ecology": ["ecosystem", "habitat", "environment", "population"],
            "Atomic Structure": ["atom", "electron", "proton", "nucleus", "orbital"],
            "Chemical Bonding": ["bond", "ionic", "covalent", "molecule"],
            "Acids and Bases": ["acid", "base", "ph", "neutralize"],
            "Newton's Laws": ["newton", "force", "motion", "inertia"],
            "Energy": ["energy", "kinetic", "potential", "work"],
            "Waves": ["wave", "frequency", "amplitude", "wavelength"],
            "Electricity": ["electric", "current", "voltage", "circuit"],
            "Magnetism": ["magnet", "magnetic", "pole", "field"],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in question_lower for kw in keywords):
                return topic

        return None

    async def import_dataset(
        self,
        max_questions: Optional[int] = None,
        subjects: Optional[List[str]] = None
    ) -> SciQImportResult:
        """
        Import SciQ dataset into Supabase

        Args:
            max_questions: Maximum number of questions to import (None for all)
            subjects: Filter by subjects (None for all)

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
            sciq_questions = await self.fetch_dataset()

            if max_questions:
                sciq_questions = sciq_questions[:max_questions]

            total_fetched = len(sciq_questions)

            if total_fetched == 0:
                return SciQImportResult(
                    total_fetched=0,
                    successfully_imported=0,
                    failed=0,
                    errors=["No questions fetched from SciQ dataset"],
                    duration_seconds=(datetime.utcnow() - start_time).total_seconds()
                )

            logger.info(f"Fetched {total_fetched} questions from SciQ dataset")

            # Get vector store
            vector_store = get_supabase_vector_store()

            # Process in batches
            for i in range(0, len(sciq_questions), self.batch_size):
                batch = sciq_questions[i:i + self.batch_size]
                batch_questions = []

                for idx, sciq_q in enumerate(batch):
                    try:
                        # Classify subject
                        subject = self._classify_subject(sciq_q)

                        # Filter by subject if specified
                        if subjects and subject not in subjects:
                            continue

                        # Create Question object
                        question = Question(
                            question_id=f"sciq_{i + idx}",
                            question_text=sciq_q.question,
                            question_type="multiple_choice",
                            subject=subject,
                            topic=self._infer_topic(sciq_q),
                            difficulty="medium",  # SciQ doesn't specify difficulty
                            grade_level=8,  # Middle/high school level
                            correct_answer=sciq_q.correct_answer,
                            incorrect_answers=[
                                sciq_q.distractor1,
                                sciq_q.distractor2,
                                sciq_q.distractor3
                            ],
                            explanation=sciq_q.support,
                            distractor1=sciq_q.distractor1,
                            distractor2=sciq_q.distractor2,
                            distractor3=sciq_q.distractor3,
                            source="sciq",
                            metadata={
                                "dataset": "SciQ",
                                "support": sciq_q.support
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
                f"SciQ import complete: {success_count}/{total_fetched} questions "
                f"imported in {duration:.2f}s"
            )

            return SciQImportResult(
                total_fetched=total_fetched,
                successfully_imported=success_count,
                failed=failed_count,
                errors=errors,
                imported_ids=imported_ids,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Error importing SciQ dataset: {e}")
            return SciQImportResult(
                total_fetched=0,
                successfully_imported=0,
                failed=0,
                errors=[str(e)],
                duration_seconds=(datetime.utcnow() - start_time).total_seconds()
            )


# ============================================================================
# Singleton Instance
# ============================================================================

_sciq_importer: Optional[SciQImporter] = None


def get_sciq_importer() -> SciQImporter:
    """Get the singleton SciQ importer instance"""
    global _sciq_importer
    if _sciq_importer is None:
        _sciq_importer = SciQImporter()
    return _sciq_importer


# ============================================================================
# Convenience Functions
# ============================================================================

async def import_sciq_dataset(
    max_questions: Optional[int] = None,
    subjects: Optional[List[str]] = None
) -> SciQImportResult:
    """
    Import SciQ dataset into Supabase

    Usage:
        # Import all questions
        result = await import_sciq_dataset()

        # Import only Biology questions
        result = await import_sciq_dataset(subjects=["Biology"])

        # Import first 100 questions
        result = await import_sciq_dataset(max_questions=100)

        print(f"Imported {result.successfully_imported} questions")
    """
    importer = get_sciq_importer()
    return await importer.import_dataset(max_questions=max_questions, subjects=subjects)
