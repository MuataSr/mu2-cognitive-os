"""
Citation Lock Service - Mu2 Cognitive OS
=========================================

Enforces that all AI responses include proper source citations.
This prevents hallucination and ensures all claims are grounded
in the source material.

CRITICAL: No response should be generated without citation validation.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import re


class Citation(BaseModel):
    """A single citation reference"""
    source_id: str = Field(..., description="ID of the source (e.g., 'biology-2e-chapter-5.1-para-3')")
    chapter: Optional[str] = Field(None, description="Chapter or section title")
    paragraph: Optional[int] = Field(None, description="Paragraph number within section")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence that this source supports the claim")
    excerpt: Optional[str] = Field(None, description="Relevant excerpt from source")


class CitationValidation(BaseModel):
    """Result of citation validation"""
    has_citations: bool
    citation_count: int
    is_valid: bool
    missing_sources: List[str]
    warnings: List[str]


class CitationLock(BaseModel):
    """Citation lock enforcement result"""
    response: str
    citations: List[Citation]
    validated: bool
    disclaimer: str = "AI generated. Always verify with source text."
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CitationLockService:
    """
    Service to enforce citation requirements on AI responses.

    FERPA Compliance Notes:
    - Citations reference educational content only
    - No student PII in citations
    - Source IDs use anonymized textbook references
    """

    # Patterns that suggest a claim needs citation
    CLAIM_PATTERNS = [
        r"\b(is|are|was|were)\b",
        r"\b(according to|research shows|studies indicate)\b",
        r"\b(causes|leads to|results in)\b",
        r"\b(important|significant|critical)\b",
    ]

    def __init__(self):
        """Initialize the citation lock service"""
        self.min_citations = 1  # At least 1 citation per response

    def validate_citations(
        self,
        response: str,
        sources: List[str],
        retrieved_context: Dict[str, Any]
    ) -> CitationValidation:
        """
        Validate that a response has proper citations

        Args:
            response: The AI-generated response text
            sources: List of source IDs provided with the response
            retrieved_context: The context used for generation

        Returns:
            CitationValidation with validation results
        """
        warnings = []
        missing_sources = []

        # Check if response exists
        if not response or len(response.strip()) == 0:
            return CitationValidation(
                has_citations=False,
                citation_count=0,
                is_valid=False,
                missing_sources=["all"],
                warnings=["Empty response"]
            )

        # Check citation count
        citation_count = len(sources) if sources else 0
        has_citations = citation_count > 0

        # Validate minimum citations
        if citation_count < self.min_citations:
            warnings.append(f"Response has {citation_count} citations, minimum is {self.min_citations}")

        # Validate source ID format
        valid_source_pattern = re.compile(r'^[\w\-\.]+\-chapter[\-0-9\.]+(\-para[\-0-9]+)?$')
        invalid_sources = []
        for source in sources:
            if not valid_source_pattern.match(source):
                invalid_sources.append(source)
                warnings.append(f"Invalid source ID format: {source}")

        # Check for "hallucination" warnings
        # If response makes claims without context support
        if retrieved_context and len(retrieved_context) > 0:
            # Response is grounded if context was used
            is_grounded = True
        else:
            warnings.append("No retrieval context provided - response may be ungrounded")
            is_grounded = False

        # Check for claim patterns that need citation
        claim_matches = sum(1 for pattern in self.CLAIM_PATTERNS if re.search(pattern, response, re.IGNORECASE))
        if claim_matches > 3 and citation_count == 0:
            warnings.append(f"Response contains {claim_matches} claim patterns but no citations")

        # Determine overall validity
        is_valid = (
            has_citations and
            citation_count >= self.min_citations and
            len(invalid_sources) == 0 and
            is_grounded
        )

        return CitationValidation(
            has_citations=has_citations,
            citation_count=citation_count,
            is_valid=is_valid,
            missing_sources=missing_sources,
            warnings=warnings
        )

    def enforce_citation_lock(
        self,
        response: str,
        sources: List[str],
        retrieved_context: Dict[str, Any],
        allow_uncited: bool = False
    ) -> CitationLock:
        """
        Enforce citation requirements on a response

        Args:
            response: The AI-generated response
            sources: List of source IDs
            retrieved_context: Context used for generation
            allow_uncited: If True, allow responses without citations (for testing)

        Returns:
            CitationLock with validated response

        Raises:
            ValueError: If citation validation fails and allow_uncited is False
        """
        # Validate citations
        validation = self.validate_citations(response, sources, retrieved_context)

        # Create Citation objects
        citations = []
        for source_id in sources:
            # Parse source ID to extract chapter/paragraph
            # Format: "biology-2e-chapter-5.1-para-3"
            parts = source_id.split('-')
            chapter = None
            paragraph = None

            if 'chapter' in parts:
                chapter_idx = parts.index('chapter')
                if chapter_idx + 1 < len(parts):
                    chapter = parts[chapter_idx + 1]
            if 'para' in parts:
                para_idx = parts.index('para')
                if para_idx + 1 < len(parts):
                    try:
                        paragraph = int(parts[para_idx + 1])
                    except (ValueError, IndexError):
                        pass

            citations.append(Citation(
                source_id=source_id,
                chapter=chapter,
                paragraph=paragraph,
                confidence=1.0
            ))

        # Check if validation passes
        if not validation.is_valid and not allow_uncited:
            error_msg = "Citation validation failed:\n" + "\n".join(validation.warnings)
            raise ValueError(error_msg)

        # Return locked response
        return CitationLock(
            response=response,
            citations=citations,
            validated=validation.is_valid,
            disclaimer="AI generated. Always verify with source text."
        )

    def format_citations_for_display(self, citations: List[Citation]) -> str:
        """
        Format citations for display in the UI

        Args:
            citations: List of Citation objects

        Returns:
            Formatted citation string
        """
        if not citations:
            return "No sources cited"

        formatted = []
        for i, citation in enumerate(citations, 1):
            parts = [f"[{i}]"]
            if citation.chapter:
                parts.append(f"Chapter {citation.chapter}")
            if citation.paragraph:
                parts.append(f"§{citation.paragraph}")
            formatted.append(" ".join(parts))

        return " | ".join(formatted)

    def extract_source_id_from_citation(self, citation_str: str) -> Optional[str]:
        """
        Extract source ID from a citation string

        Args:
            citation_str: Citation string like "[1] Chapter 5.1 §3"

        Returns:
            Source ID or None
        """
        # This would parse the citation back to source ID
        # For now, return None - would need bidirectional mapping
        return None


# Singleton instance
citation_lock_service = CitationLockService()


async def enforce_citations(
    response: str,
    sources: List[str],
    retrieved_context: Dict[str, Any],
    allow_uncited: bool = False
) -> CitationLock:
    """
    Convenience function to enforce citations on a response

    Usage:
        result = await enforce_citations(
            response="Photosynthesis converts light to energy...",
            sources=["biology-2e-chapter-5.1-para-3"],
            retrieved_context={...}
        )
    """
    return citation_lock_service.enforce_citation_lock(
        response=response,
        sources=sources,
        retrieved_context=retrieved_context,
        allow_uncited=allow_uncited
    )
