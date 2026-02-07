"""
PII Pattern Detection for Mu2 Cognitive OS
Regex patterns for detecting Personally Identifiable Information (PII)

This module provides pattern-based detection for common PII types.
Used by the anonymization service to identify and mask sensitive information.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class PIIType(Enum):
    """Types of PII that can be detected"""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    ADDRESS = "address"
    NAME = "name"
    USERNAME = "username"
    URL = "url"


@dataclass
class PIIEntity:
    """A detected PII entity"""
    type: PIIType
    text: str
    start: int
    end: int
    confidence: float
    label: str


class PIIPatterns:
    """
    Regex patterns for detecting PII in text.

    FERPA Compliance Note:
    - These patterns help identify potential PII before sending data to external services
    - Detection is conservative (may have false positives, should minimize false negatives)
    - All detected PII should be reviewed and masked
    """

    # Email pattern (most common)
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        re.IGNORECASE
    )

    # Phone number patterns (US formats)
    PHONE_PATTERNS = [
        # (123) 456-7890
        re.compile(r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}'),
        # 123-456-7890, 123.456.7890, 123 456 7890
        re.compile(r'\d{3}[-.\s]\d{3}[-.\s]\d{4}'),
        # 1234567890, 12345678901
        re.compile(r'\b\d{10}\b'),
        re.compile(r'\b1?\d{10}\b'),
    ]

    # SSN pattern (###-##-####)
    SSN_PATTERN = re.compile(
        r'\b\d{3}-\d{2}-\d{4}\b'
    )

    # Credit card patterns (simplified - detects common formats)
    CREDIT_CARD_PATTERNS = [
        # Visa: starts with 4, 16 digits
        re.compile(r'\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        # MasterCard: starts with 5, 16 digits
        re.compile(r'\b5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        # Amex: starts with 34/37, 15 digits
        re.compile(r'\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b'),
    ]

    # IP address patterns
    IP_V4_PATTERN = re.compile(
        r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    )

    # Date of birth patterns (common formats)
    DOB_PATTERNS = [
        # MM/DD/YYYY, MM-DD-YYYY
        re.compile(r'\b(0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])[-/](19|20)\d{2}\b'),
        # DD/MM/YYYY, DD-MM-YYYY
        re.compile(r'\b(0[1-9]|[12]\d|3[01])[-/](0[1-9]|1[0-2])[-/](19|20)\d{2}\b'),
        # YYYY-MM-DD (ISO format)
        re.compile(r'\b(19|20)\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b'),
    ]

    # Address patterns (street addresses - simplified)
    ADDRESS_PATTERNS = [
        # Number + Street Name
        re.compile(r'\b\d+\s+[A-Z][a-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd|Way|Court|Ct|Place|Pl)\b', re.IGNORECASE),
    ]

    # Username/handle patterns
    USERNAME_PATTERNS = [
        # @username
        re.compile(r'@[A-Za-z0-9_]{3,15}'),
        # Common username patterns
        re.compile(r'\b[A-Za-z0-9_]{3,15}\s+(?:said|wrote|commented)', re.IGNORECASE),
    ]

    # URL pattern
    URL_PATTERN = re.compile(
        r'https?://(?:www\.)?[A-Za-z0-9-]+\.[A-Za-z]{2,}(?:/\S*)?',
        re.IGNORECASE
    )

    # Common first names (for context-aware detection)
    COMMON_FIRST_NAMES = {
        'james', 'john', 'robert', 'michael', 'william', 'david', 'richard', 'joseph',
        'thomas', 'charles', 'christopher', 'daniel', 'matthew', 'anthony', 'donald',
        'mark', 'paul', 'steven', 'andrew', 'kenneth', 'joshua', 'kevin', 'brian',
        'george', 'edward', 'ronald', 'timothy', 'jason', 'jeffrey', 'ryan', 'jacob',
        'gary', 'nicholas', 'eric', 'jonathan', 'stephen', 'larry', 'justin', 'scott',
        'brandon', 'benjamin', 'samuel', 'raymond', 'gregory', 'frank', 'alexander',
        'mary', 'patricia', 'jennifer', 'linda', 'elizabeth', 'barbara', 'susan',
        'jessica', 'sarah', 'karen', 'nancy', 'lisa', 'betty', 'margaret', 'sandra',
        'ashley', 'kimberly', 'emily', 'donna', 'michelle', 'dorothy', 'carol',
        'amanda', 'melissa', 'deborah', 'stephanie', 'rebecca', 'sharon', 'laura',
        'cynthia', 'kathleen', 'amy', 'angela', 'shirley', 'anna', 'brenda', 'pamela',
        'emma', 'olivia', 'cassandra', 'sophia', 'isabella', 'charlotte', 'mia',
        'amelia', 'harper', 'evelyn', 'abigail', 'emily', 'elizabeth', 'samantha',
        'alexander', 'max', 'jacob', 'michael', 'daniel', 'henry', 'ryan', 'noah'
    }

    # Common last names (for context-aware detection)
    COMMON_LAST_NAMES = {
        'smith', 'johnson', 'williams', 'brown', 'jones', 'garcia', 'miller', 'davis',
        'rodriguez', 'martinez', 'hernandez', 'lopez', 'gonzalez', 'wilson', 'anderson',
        'thomas', 'taylor', 'moore', 'jackson', 'martin', 'lee', 'perez', 'thompson',
        'white', 'harris', 'sanchez', 'clark', 'ramirez', 'lewis', 'robinson', 'walker',
        'young', 'allen', 'king', 'wright', 'scott', 'torres', 'nguyen', 'hill', 'flores',
        'green', 'adams', 'nelson', 'baker', 'hall', 'rivera', 'campbell', 'mitchell',
        'carter', 'roberts'
    }

    # Name context patterns (indicates a name might be nearby)
    NAME_CONTEXT_PATTERNS = [
        re.compile(r'\b(?:my name is|i am|i\'m|call me|this is)\s+([A-Z][a-z]+)', re.IGNORECASE),
        re.compile(r'\b(?:mr\.|mrs\.|ms\.|dr\.|prof\.)\s+([A-Z][a-z]+)', re.IGNORECASE),
    ]

    @classmethod
    def detect_all_pii(cls, text: str) -> List[PIIEntity]:
        """
        Detect all PII entities in the given text.

        Returns a list of PIIEntity objects sorted by position.
        """
        detected = []

        # Detect emails
        for match in cls.EMAIL_PATTERN.finditer(text):
            detected.append(PIIEntity(
                type=PIIType.EMAIL,
                text=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.95,
                label="[EMAIL]"
            ))

        # Detect phone numbers
        for pattern in cls.PHONE_PATTERNS:
            for match in pattern.finditer(text):
                detected.append(PIIEntity(
                    type=PIIType.PHONE,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.85,
                    label="[PHONE]"
                ))

        # Detect SSNs
        for match in cls.SSN_PATTERN.finditer(text):
            detected.append(PIIEntity(
                type=PIIType.SSN,
                text=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.90,
                label="[SSN]"
            ))

        # Detect credit cards
        for pattern in cls.CREDIT_CARD_PATTERNS:
            for match in pattern.finditer(text):
                detected.append(PIIEntity(
                    type=PIIType.CREDIT_CARD,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.80,
                    label="[CREDIT_CARD]"
                ))

        # Detect IP addresses
        for match in cls.IP_V4_PATTERN.finditer(text):
            detected.append(PIIEntity(
                type=PIIType.IP_ADDRESS,
                text=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.75,
                label="[IP]"
            ))

        # Detect dates of birth
        for pattern in cls.DOB_PATTERNS:
            for match in pattern.finditer(text):
                detected.append(PIIEntity(
                    type=PIIType.DATE_OF_BIRTH,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.60,
                    label="[DATE]"
                ))

        # Detect addresses
        for pattern in cls.ADDRESS_PATTERNS:
            for match in pattern.finditer(text):
                detected.append(PIIEntity(
                    type=PIIType.ADDRESS,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.55,
                    label="[ADDRESS]"
                ))

        # Detect URLs
        for match in cls.URL_PATTERN.finditer(text):
            detected.append(PIIEntity(
                type=PIIType.URL,
                text=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.90,
                label="[URL]"
            ))

        # Detect usernames/handles
        for pattern in cls.USERNAME_PATTERNS:
            for match in pattern.finditer(text):
                detected.append(PIIEntity(
                    type=PIIType.USERNAME,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.65,
                    label="[USERNAME]"
                ))

        # Detect names (context-based)
        detected.extend(cls._detect_names(text))

        # Sort by position and remove overlaps (keep higher confidence)
        detected.sort(key=lambda x: x.start)
        detected = cls._remove_overlaps(detected)

        return detected

    @classmethod
    def _detect_names(cls, text: str) -> List[PIIEntity]:
        """
        Detect potential names in text using context clues.
        This is less accurate than other pattern matching.
        """
        detected = []

        # Check for context patterns
        for pattern in cls.NAME_CONTEXT_PATTERNS:
            for match in pattern.finditer(text):
                name_text = match.group(1)
                # Check if it's a common first name
                if name_text.lower() in cls.COMMON_FIRST_NAMES:
                    detected.append(PIIEntity(
                        type=PIIType.NAME,
                        text=name_text,
                        start=match.start(1),
                        end=match.end(1),
                        confidence=0.50,  # Lower confidence for names
                        label="[NAME]"
                    ))

        return detected

    @classmethod
    def _remove_overlaps(cls, entities: List[PIIEntity]) -> List[PIIEntity]:
        """
        Remove overlapping entities, keeping the one with higher confidence.
        """
        if not entities:
            return entities

        result = [entities[0]]
        for entity in entities[1:]:
            last = result[-1]
            # Check if current entity overlaps with last kept entity
            if entity.start < last.end:
                # Keep the one with higher confidence
                if entity.confidence > last.confidence:
                    result[-1] = entity
            else:
                result.append(entity)

        return result

    @classmethod
    def mask_pii(cls, text: str, entities: List[PIIEntity], mask_char: str = '*') -> str:
        """
        Replace detected PII entities with mask characters.
        """
        if not entities:
            return text

        # Sort entities by position (reverse order to avoid index shifting)
        sorted_entities = sorted(entities, key=lambda x: x.start, reverse=True)

        result = text
        for entity in sorted_entities:
            # Replace with label instead of just mask chars for better readability
            result = result[:entity.start] + entity.label + result[entity.end:]

        return result


# Convenience function for quick PII detection
def detect_pii(text: str) -> List[Dict[str, Any]]:
    """
    Quick function to detect PII in text.

    Returns a list of dictionaries with PII information.
    """
    entities = PIIPatterns.detect_all_pii(text)
    return [
        {
            "type": e.type.value,
            "text": e.text,
            "start": e.start,
            "end": e.end,
            "confidence": e.confidence,
            "label": e.label
        }
        for e in entities
    ]


def mask_pii_in_text(text: str, mask_char: str = '*') -> tuple[str, List[Dict[str, Any]]]:
    """
    Mask PII in text and return both the masked text and detected entities.

    Returns:
        tuple: (masked_text, detected_entities)
    """
    entities = PIIPatterns.detect_all_pii(text)
    masked_text = PIIPatterns.mask_pii(text, entities, mask_char)
    return masked_text, detect_pii(text)
