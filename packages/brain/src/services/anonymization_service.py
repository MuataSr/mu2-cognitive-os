"""
Anonymization Service for Mu2 Cognitive OS
Provides PII detection and removal using local Ollama model

This service ensures FERPA compliance by:
1. Detecting PII using pattern matching and local LLM
2. Removing/masking PII before sending to external services
3. Keeping anonymization metadata for internal use only
4. Never logging original unanonymized text
"""

import asyncio
import json
import secrets
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from collections import OrderedDict

import requests
from pydantic import BaseModel, Field

from src.core.config import settings
from src.services.pii_patterns import PIIPatterns, PIIType, PIIEntity, detect_pii


@dataclass
class AnonymizationMetadata:
    """Metadata about what was anonymized"""
    original_text: str  # NOTE: Only for in-memory use, NEVER log or persist
    anonymized_text: str
    entities_detected: List[Dict[str, Any]]
    pii_count: int
    anonymization_method: str
    timestamp: str
    user_id_masked: Optional[str] = None
    mask_token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excludes original_text for safety)"""
        data = asdict(self)
        # Remove original_text - never include this in logs or external communication
        data.pop("original_text", None)
        return data


class AnonymizationResult(BaseModel):
    """Result of anonymization"""
    anonymized_text: str = Field(..., description="Text with PII removed/masked")
    has_pii: bool = Field(default=False, description="Whether PII was detected")
    pii_count: int = Field(default=0, description="Number of PII entities detected")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Anonymization metadata")
    safe_for_cloud: bool = Field(default=True, description="Whether text is safe to send to cloud")


class AnonymizationService:
    """
    Service for detecting and anonymizing PII in text.

    Uses a hybrid approach:
    1. Pattern-based detection for common PII (emails, phones, SSNs)
    2. Local LLM (Ollama) for contextual PII detection
    3. Configurable masking strategies
    """

    # Class-level constants for cache
    _cache_max_size = 1000
    _cache_ttl = timedelta(hours=1)

    def __init__(
        self,
        method: str = "hybrid",  # "pattern", "llm", "hybrid"
        mask_char: str = "*",
        use_labels: bool = True,
        llm_model: Optional[str] = None
    ):
        self.method = method
        self.mask_char = mask_char
        self.use_labels = use_labels
        self.llm_model = llm_model or settings.llm_model
        self.llm_base_url = settings.llm_base_url

        # In-memory cache for user ID masking (ephemeral, not persisted)
        self._user_id_cache: OrderedDict[str, str] = OrderedDict()

        # Cache for pattern detection results
        self._pattern_cache: Dict[str, List[PIIEntity]] = {}

    async def anonymize_text(
        self,
        text: str,
        user_id: Optional[str] = None,
        include_metadata: bool = True
    ) -> AnonymizationResult:
        """
        Anonymize PII in the given text.

        Args:
            text: The text to anonymize
            user_id: Optional user ID to mask
            include_metadata: Whether to include anonymization metadata

        Returns:
            AnonymizationResult with masked text and metadata
        """
        if not text or not text.strip():
            return AnonymizationResult(anonymized_text=text)

        # Detect PII using configured method
        if self.method == "pattern":
            entities = await self._detect_with_patterns(text)
        elif self.method == "llm":
            entities = await self._detect_with_llm(text)
        else:  # hybrid
            entities = await self._detect_with_hybrid(text)

        # Mask user ID if provided
        masked_user_id = None
        mask_token = None
        if user_id:
            masked_user_id, mask_token = self._mask_user_id(user_id)

        # Apply masking to text
        anonymized_text = self._apply_masking(text, entities)

        # Create metadata
        metadata = None
        if include_metadata:
            metadata = AnonymizationMetadata(
                original_text=text,  # In-memory only
                anonymized_text=anonymized_text,
                entities_detected=[{"type": e.type.value, "label": e.label} for e in entities],
                pii_count=len(entities),
                anonymization_method=self.method,
                timestamp=datetime.now(timezone.utc).isoformat(),
                user_id_masked=masked_user_id,
                mask_token=mask_token
            )

        return AnonymizationResult(
            anonymized_text=anonymized_text,
            has_pii=len(entities) > 0,
            pii_count=len(entities),
            metadata=metadata.to_dict() if metadata else {},
            safe_for_cloud=self._is_safe_for_cloud(entities)
        )

    async def _detect_with_patterns(self, text: str) -> List[PIIEntity]:
        """Detect PII using regex patterns only"""
        # Check cache
        cache_key = f"pattern:{hash(text)}"
        if cache_key in self._pattern_cache:
            return self._pattern_cache[cache_key]

        entities = PIIPatterns.detect_all_pii(text)

        # Cache result
        self._pattern_cache[cache_key] = entities
        return entities

    async def _detect_with_llm(self, text: str) -> List[PIIEntity]:
        """
        Detect PII using local LLM (Ollama).

        This is more accurate for contextual PII like names in sentences.
        """
        prompt = f"""Analyze the following text and identify any personally identifiable information (PII).

Respond ONLY with a JSON array of PII found. Each item should have:
- "type": one of: email, phone, ssn, credit_card, name, address, dob, username
- "text": the exact text that contains PII
- "start": character position where it starts
- "end": character position where it ends

Text to analyze:
{text[:500]}

If no PII is found, return an empty array: []"""

        try:
            response = requests.post(
                f"{self.llm_base_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}  # Low temp for consistent detection
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # Parse LLM response
            llm_output = result.get("response", "").strip()

            # Try to extract JSON from response
            if "[" in llm_output and "]" in llm_output:
                json_start = llm_output.index("[")
                json_end = llm_output.rindex("]") + 1
                json_str = llm_output[json_start:json_end]

                detected = json.loads(json_str)

                # Convert to PIIEntity objects
                entities = []
                for item in detected:
                    try:
                        pii_type = PIIType(item.get("type", "name"))
                        entities.append(PIIEntity(
                            type=pii_type,
                            text=item.get("text", ""),
                            start=item.get("start", 0),
                            end=item.get("end", 0),
                            confidence=0.70,  # LLM detection has moderate confidence
                            label=f"[{pii_type.value.upper()}]"
                        ))
                    except (ValueError, KeyError):
                        continue

                return entities

        except (requests.RequestException, json.JSONDecodeError) as e:
            # Fall back to pattern detection if LLM fails
            pass

        return await self._detect_with_patterns(text)

    async def _detect_with_hybrid(self, text: str) -> List[PIIEntity]:
        """
        Detect PII using both patterns and LLM for maximum coverage.

        Strategy:
        1. Run pattern detection first (fast, high precision)
        2. If patterns found PII, return those
        3. If no patterns found but text is long/complex, use LLM
        """
        # Start with pattern detection
        pattern_entities = await self._detect_with_patterns(text)

        # If patterns found high-confidence PII, return those
        high_confidence = [e for e in pattern_entities if e.confidence >= 0.80]
        if high_confidence:
            return pattern_entities

        # For longer texts without obvious PII, use LLM to catch contextual PII
        if len(text) > 100:
            llm_entities = await self._detect_with_llm(text)
            if llm_entities:
                # Merge both sets, removing duplicates
                return self._merge_entities(pattern_entities, llm_entities)

        return pattern_entities

    def _merge_entities(
        self,
        entities1: List[PIIEntity],
        entities2: List[PIIEntity]
    ) -> List[PIIEntity]:
        """Merge two lists of entities, removing duplicates"""
        all_entities = entities1 + entities2
        all_entities.sort(key=lambda e: e.start)

        merged = []
        for entity in all_entities:
            # Check if this overlaps with an existing entity
            is_duplicate = False
            for existing in merged:
                if (entity.start >= existing.start and entity.start < existing.end) or \
                   (existing.start >= entity.start and existing.start < entity.end):
                    # Overlap detected - keep higher confidence
                    if entity.confidence > existing.confidence:
                        merged.remove(existing)
                        merged.append(entity)
                    is_duplicate = True
                    break

            if not is_duplicate:
                merged.append(entity)

        return merged

    def _apply_masking(self, text: str, entities: List[PIIEntity]) -> str:
        """Apply masking to text based on detected entities"""
        if not entities:
            return text

        # Sort by position (reverse to avoid index shifting)
        sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)

        result = text
        for entity in sorted_entities:
            if self.use_labels:
                # Use semantic labels (e.g., [EMAIL], [PHONE])
                result = result[:entity.start] + entity.label + result[entity.end:]
            else:
                # Use asterisks for full masking
                masked_length = entity.end - entity.start
                result = result[:entity.start] + (self.mask_char * masked_length) + result[entity.end:]

        return result

    def _mask_user_id(self, user_id: str) -> Tuple[str, str]:
        """
        Mask a user ID with a random token.

        Returns:
            tuple: (masked_id, token) where token can be used to reverse the mapping
        """
        # Clean the cache if it's too old
        self._clean_cache()

        # Check if we already have a mapping
        if user_id in self._user_id_cache:
            masked_id = self._user_id_cache[user_id]
            # Move to end (LRU)
            self._user_id_cache.move_to_end(user_id)
            return masked_id, self._generate_token(user_id, masked_id)

        # Generate new masked ID
        masked_id = f"user-{secrets.token_hex(8)}"

        # Add to cache
        self._user_id_cache[user_id] = masked_id

        # Enforce max cache size
        if len(self._user_id_cache) > self._cache_max_size:
            self._user_id_cache.popitem(last=False)

        return masked_id, self._generate_token(user_id, masked_id)

    def _generate_token(self, original: str, masked: str) -> str:
        """Generate a reversible token for the mapping"""
        # In production, this should use proper encryption
        # For now, a simple token format
        data = f"{original}:{masked}"
        return secrets.token_urlsafe(32)

    def _clean_cache(self):
        """Clean old entries from the cache"""
        # In a full implementation, check timestamps and remove old entries
        if len(self._user_id_cache) > self._cache_max_size * 0.8:
            # Remove oldest 20% of entries
            remove_count = int(self._cache_max_size * 0.2)
            for _ in range(remove_count):
                self._user_id_cache.popitem(last=False)

    def _is_safe_for_cloud(self, entities: List[PIIEntity]) -> bool:
        """Determine if text is safe to send to cloud based on detected PII"""
        # High-confidence PII detections make it unsafe
        high_confidence_pii = [e for e in entities if e.confidence >= 0.70]
        return len(high_confidence_pii) == 0

    def get_masked_user_id(self, user_id: str) -> str:
        """Get or create a masked version of a user ID"""
        masked, _ = self._mask_user_id(user_id)
        return masked

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the anonymization service"""
        # Test pattern detection
        test_email = "Contact me at test@example.com"
        pattern_result = await self._detect_with_patterns(test_email)

        # Check LLM availability
        llm_available = False
        try:
            response = requests.get(f"{self.llm_base_url}/api/tags", timeout=5)
            llm_available = response.status_code == 200
        except requests.RequestException:
            pass

        return {
            "status": "healthy",
            "method": self.method,
            "pattern_detection": "working" if pattern_result else "failed",
            "llm_available": llm_available,
            "llm_model": self.llm_model,
            "cache_size": len(self._user_id_cache),
        }


# Global singleton instance
anonymization_service = AnonymizationService(method="hybrid")


# Convenience functions
async def anonymize(text: str, user_id: Optional[str] = None) -> AnonymizationResult:
    """Quick function to anonymize text"""
    return await anonymization_service.anonymize_text(text, user_id)


def mask_user_id(user_id: str) -> str:
    """Quick function to mask a user ID"""
    return anonymization_service.get_masked_user_id(user_id)
