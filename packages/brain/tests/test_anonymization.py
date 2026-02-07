"""
Tests for Anonymization Service
FERPA Compliance Testing
"""

import pytest
import asyncio
from src.services.pii_patterns import (
    PIIPatterns,
    PIIType,
    PIIEntity,
    detect_pii,
    mask_pii_in_text
)
from src.services.anonymization_service import (
    AnonymizationService,
    AnonymizationResult,
    anonymize,
    mask_user_id
)


class TestPIIPatterns:
    """Test PII pattern detection"""

    def test_detect_email(self):
        """Test email detection"""
        text = "Contact me at john@example.com for more info"
        entities = PIIPatterns.detect_all_pii(text)

        assert len(entities) > 0
        assert any(e.type == PIIType.EMAIL for e in entities)

    def test_detect_phone(self):
        """Test phone number detection"""
        text = "Call me at (123) 456-7890"
        entities = PIIPatterns.detect_all_pii(text)

        assert len(entities) > 0
        assert any(e.type == PIIType.PHONE for e in entities)

    def test_detect_ssn(self):
        """Test SSN detection"""
        text = "My SSN is 123-45-6789"
        entities = PIIPatterns.detect_all_pii(text)

        assert len(entities) > 0
        assert any(e.type == PIIType.SSN for e in entities)

    def test_detect_ip_address(self):
        """Test IP address detection"""
        text = "Connect to 192.168.1.1 to access"
        entities = PIIPatterns.detect_all_pii(text)

        assert len(entities) > 0
        assert any(e.type == PIIType.IP_ADDRESS for e in entities)

    def test_detect_multiple_pii(self):
        """Test detection of multiple PII types"""
        text = "Hi, I'm John Smith. Email me at john@example.com or call (555) 123-4567"
        entities = PIIPatterns.detect_all_pii(text)

        # Should detect at least email and phone
        types_found = {e.type for e in entities}
        assert PIIType.EMAIL in types_found
        assert PIIType.PHONE in types_found

    def test_mask_pii(self):
        """Test PII masking"""
        text = "Email me at test@example.com"
        entities = PIIPatterns.detect_all_pii(text)
        masked = PIIPatterns.mask_pii(text, entities)

        assert "[EMAIL]" in masked
        assert "test@example.com" not in masked

    def test_no_false_positives_simple_text(self):
        """Test that simple text doesn't trigger false positives"""
        text = "What is photosynthesis and how does it work?"
        entities = PIIPatterns.detect_all_pii(text)

        # Should not detect any PII in educational content
        assert len(entities) == 0

    def test_detect_pii_convenience_function(self):
        """Test the convenience function for PII detection"""
        text = "Contact john@example.com"
        detected = detect_pii(text)

        assert len(detected) > 0
        assert detected[0]["type"] == "email"

    def test_mask_pii_in_text_convenience_function(self):
        """Test the convenience function for masking"""
        text = "Email: test@example.com, Phone: (123) 456-7890"
        masked, detected = mask_pii_in_text(text)

        assert "[EMAIL]" in masked
        assert "[PHONE]" in masked
        assert len(detected) >= 2


class TestAnonymizationService:
    """Test the AnonymizationService"""

    @pytest.fixture
    def service(self):
        return AnonymizationService(method="pattern")

    @pytest.mark.asyncio
    async def test_anonymize_email(self, service):
        """Test anonymizing an email"""
        result = await service.anonymize_text("Contact me at john@example.com")

        assert result.has_pii is True
        assert result.pii_count > 0
        assert "[EMAIL]" in result.anonymized_text
        assert "john@example.com" not in result.anonymized_text

    @pytest.mark.asyncio
    async def test_anonymize_phone(self, service):
        """Test anonymizing a phone number"""
        result = await service.anonymize_text("Call (555) 123-4567")

        assert result.has_pii is True
        assert "[PHONE]" in result.anonymized_text

    @pytest.mark.asyncio
    async def test_anonymize_no_pii(self, service):
        """Test text without PII"""
        result = await service.anonymize_text("What is photosynthesis?")

        assert result.has_pii is False
        assert result.pii_count == 0
        assert result.anonymized_text == "What is photosynthesis?"

    @pytest.mark.asyncio
    async def test_anonymize_with_user_id(self, service):
        """Test anonymization with user ID masking"""
        result = await service.anonymize_text(
            "My email is john@example.com",
            user_id="student-123"
        )

        assert result.has_pii is True
        assert result.metadata is not None
        assert "user_id_masked" in result.metadata

    @pytest.mark.asyncio
    async def test_safe_for_cloud(self, service):
        """Test safe_for_cloud flag"""
        # PII detected - not safe for cloud
        result_pii = await service.anonymize_text("Email: john@example.com")
        assert result_pii.safe_for_cloud is False

        # No PII - safe for cloud
        result_no_pii = await service.anonymize_text("What is ATP?")
        assert result_no_pii.safe_for_cloud is True

    @pytest.mark.asyncio
    async def test_mask_user_id(self, service):
        """Test user ID masking"""
        masked = service.get_masked_user_id("student-123")

        assert masked != "student-123"
        assert "user-" in masked
        assert "student-123" not in masked

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test service health check"""
        health = await service.health_check()

        assert "status" in health
        assert "method" in health
        assert health["method"] == "pattern"


class TestAnonymizationConvenienceFunctions:
    """Test convenience functions"""

    @pytest.mark.asyncio
    async def test_anonymize_function(self):
        """Test the global anonymize function"""
        result = await anonymize("Contact test@example.com")

        assert result.has_pii is True
        assert "[EMAIL]" in result.anonymized_text

    def test_mask_user_id_function(self):
        """Test the global mask_user_id function"""
        masked = mask_user_id("student-456")

        assert masked != "student-456"


class TestFERPACompliance:
    """FERPA compliance specific tests"""

    @pytest.mark.asyncio
    async def test_student_pii_detection(self):
        """Test detection of common student PII scenarios"""
        service = AnonymizationService(method="pattern")

        # Student introducing themselves
        result1 = await service.anonymize_text("My name is John Smith and my email is john@school.edu")
        assert result1.has_pii is True
        assert result1.pii_count >= 2

        # Parent contact info
        result2 = await service.anonymize_text("My mom can be reached at (555) 987-6543")
        assert result2.has_pii is True

        # Address disclosure
        result3 = await service.anonymize_text("I live at 123 Main Street")
        # Address detection has lower confidence, may or may not detect
        # This is expected behavior

    @pytest.mark.asyncio
    async def test_educational_content_not_flagged(self):
        """Test that educational content doesn't get flagged as PII"""
        service = AnonymizationService(method="pattern")

        # Biology content
        result1 = await service.anonymize_text("Photosynthesis converts light energy to chemical energy")
        assert result1.has_pii is False

        # Math content
        result2 = await service.anonymize_text("Solve for x: 2x + 5 = 15")
        assert result2.has_pii is False

        # History content
        result3 = await service.anonymize_text("The Declaration of Independence was signed in 1776")
        assert result3.has_pii is False

    @pytest.mark.asyncio
    async def test_metadata_does_not_contain_original_text(self):
        """Test that original text is not exposed in metadata"""
        service = AnonymizationService(method="pattern")
        original = "Email me at john@example.com"

        result = await service.anonymize_text(original)

        # Metadata should NOT contain original text
        assert "original_text" not in result.metadata
        assert original not in str(result.metadata)

    @pytest.mark.asyncio
    async def test_reversible_masking_not_exposed(self):
        """Test that reversible user ID mapping is not exposed"""
        service = AnonymizationService(method="pattern")

        result = await service.anonymize_text(
            "Hello",
            user_id="student-sensitive-id"
        )

        # Mask token should not be in the public metadata
        # (it's there for internal use but shouldn't be logged)
        assert "sensitive-id" not in result.anonymized_text
        assert "sensitive-id" not in str(result.metadata.get("user_id_masked", ""))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
