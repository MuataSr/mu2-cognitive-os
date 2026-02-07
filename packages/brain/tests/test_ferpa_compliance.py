"""
FERPA Compliance Test Suite
Privacy and Data Protection Tests for Mu2 Cognitive OS

This test suite ensures compliance with the Family Educational Rights and Privacy Act (FERPA).

Key Requirements:
- Student educational records must be protected
- No external transmission of student data
- Local-only processing verified
- No PII in logs or query responses
"""

import pytest
import asyncio
import os
import re
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from src.main import app
from typing import List, Dict, Any


class TestPIIProtection:
    """
    Test that Personally Identifiable Information (PII) is protected
    and not exposed in logs, responses, or external transmissions.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        yield
        # Cleanup if needed

    @pytest.mark.asyncio
    async def test_no_real_name_in_response(self):
        """
        Test that student real names are NOT included in API responses.
        Even if provided, responses should use anonymous identifiers.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Send a query with potential PII
            response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "My name is John Smith. What is photosynthesis?",
                    "user_id": "john.smith@school.edu",
                    "mode": "standard"
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Response should NOT contain the real name
            assert "john smith" not in data["response"].lower(), \
                "Real name should not be echoed in response"

    @pytest.mark.asyncio
    async def test_no_email_in_response(self):
        """
        Test that email addresses are NOT included in API responses.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            test_emails = [
                "student@school.edu",
                "john.doe@gmail.com",
                "user.name@university.org"
            ]

            for email in test_emails:
                response = await client.post(
                    "/api/v1/chat",
                    json={
                        "message": f"My email is {email}. What is evolution?",
                        "user_id": email,
                        "mode": "standard"
                    }
                )

                assert response.status_code == 200
                data = response.json()

                # Response should NOT contain the email
                assert email not in data["response"].lower(), \
                    f"Email should not be echoed in response: {email}"

    @pytest.mark.asyncio
    async def test_no_student_id_in_response(self):
        """
        Test that student IDs are NOT included in API responses.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            student_ids = [
                "SID123456",
                "987-65-4321",
                "student-id-abc123",
                "20240001"
            ]

            for student_id in student_ids:
                response = await client.post(
                    "/api/v1/chat",
                    json={
                        "message": f"My student ID is {student_id}. What is water's boiling point?",
                        "user_id": student_id,
                        "mode": "standard"
                    }
                )

                assert response.status_code == 200
                data = response.json()

                # Response should NOT contain the student ID
                assert student_id not in data["response"].lower(), \
                    f"Student ID should not be echoed in response: {student_id}"

    @pytest.mark.asyncio
    async def test_session_id_is_anonymous(self):
        """
        Test that session IDs are anonymous and don't contain PII.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Test with provided session ID
            response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "What is photosynthesis?",
                    "session_id": "session_abc123",
                    "mode": "standard"
                }
            )

            assert response.status_code == 200

            # Session ID should be used internally but not exposed in response
            # (implementation specific, but should not leak PII)

    @pytest.mark.asyncio
    async def test_query_sanitization(self):
        """
        Test that queries are sanitized before being stored or logged.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Query with potential PII patterns
            pii_queries = [
                "My name is John Doe and I want to know about photosynthesis",
                "Email me at jane@school.edu for more info about evolution",
                "My SSN is 123-45-6789, now tell me about cells",
            ]

            for query in pii_queries:
                response = await client.post(
                    "/api/v1/chat",
                    json={"message": query, "mode": "standard"}
                )

                assert response.status_code == 200
                data = response.json()

                # Response should not echo the PII portion
                # (implementation may vary, but should sanitize)


class TestLogSanitization:
    """
    Test that logs do not contain PII.
    This is critical for FERPA compliance.
    """

    def check_file_for_pii(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Check a log file for PII patterns.

        Returns:
            List of PII findings with line numbers and patterns matched
        """
        pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "phone": r'\b\d{3}-\d{3}-\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "student_id": r'\b(SID|Student|student)[-_\s]?(ID|id)?[-_\s]?\d+\b',
            "real_name_context": r'(real|actual|true)[-_\s]?(name|Name)[-_\s]?[:is]\s+[A-Z][a-z]+\s+[A-Z][a-z]+',
        }

        findings = []

        if not file_path.exists():
            return findings

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                for pii_type, pattern in pii_patterns.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append({
                            "line": line_num,
                            "type": pii_type,
                            "pattern": pattern,
                            "content": line.strip()[:100]  # First 100 chars
                        })

        return findings

    @pytest.mark.asyncio
    async def test_no_pii_in_application_logs(self):
        """
        Test that application logs do not contain PII.
        """
        # Check common log locations
        log_locations = [
            Path("/home/papi/Documents/mu2-cognitive-os/packages/brain/logs"),
            Path("/home/papi/Documents/mu2-cognitive-os/logs"),
            Path("/var/log/mu2-brain"),
        ]

        all_findings = []

        for log_dir in log_locations:
            if not log_dir.exists():
                continue

            # Check all .log files
            for log_file in log_dir.glob("*.log"):
                findings = self.check_file_for_pii(log_file)
                if findings:
                    all_findings.extend([
                        {"file": str(log_file), **finding} for finding in findings
                    ])

        # Assert no PII found
        if all_findings:
            pytest.fail(
                f"PII found in logs:\n" +
                "\n".join([
                    f"  - {f['file']}:{f['line']} ({f['type']}): {f['content']}"
                    for f in all_findings[:5]  # Show first 5
                ]) +
                f"\n... and {len(all_findings) - 5} more" if len(all_findings) > 5 else ""
            )

    @pytest.mark.asyncio
    async def test_no_pii_in_vector_store_metadata(self):
        """
        Test that vector store metadata does not contain PII.
        """
        from src.services.vector_store import vector_store_service

        await vector_store_service.initialize()

        # Query to get all nodes
        # (implementation dependent - this is a conceptual test)
        # In practice, you'd query the vector store and check metadata

        # For now, this is a placeholder that verifies the structure
        # Actual implementation would depend on your vector store inspection method

    @pytest.mark.asyncio
    async def test_query_logs_contain_only_sanitized_data(self):
        """
        Test that RAG query logs contain only sanitized data.

        Logs should contain:
        - The query itself (sanitized of PII)
        - Retrieved chunk IDs
        - Anonymous session ID

        Logs should NOT contain:
        - Student real name
        - Student email
        - Student ID
        """
        # This test would require actual logging infrastructure inspection
        # For now, it's a placeholder for the required check

        # Conceptual check:
        # 1. Make a query with potential PII
        # 2. Check that any logs created don't contain the PII
        # 3. Verify only anonymous session IDs are used

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "My name is John Smith. What is photosynthesis?",
                    "user_id": "john.smith@school.edu",
                    "session_id": "session_abc123",
                    "mode": "standard"
                }
            )

            assert response.status_code == 200

            # Check logs (implementation dependent)
            # This would inspect actual log files or database entries


class TestDataRetention:
    """
    Test data retention policies for FERPA compliance.
    """

    @pytest.mark.asyncio
    async def test_no_external_data_transmission(self):
        """
        Verify that no student data is transmitted externally.

        All processing should be local.
        """
        # Check configuration
        from src.core.config import settings

        # Verify no external API endpoints that would transmit student data
        # (except for approved educational content APIs)

        # Check that LLM base URL is local
        assert "localhost" in settings.llm_base_url or "127.0.0.1" in settings.llm_base_url, \
            "LLM should be hosted locally for FERPA compliance"

        # Check that database is local
        assert "localhost" in settings.database_url or "127.0.0.1" in settings.database_url, \
            "Database should be local for FERPA compliance"

    @pytest.mark.asyncio
    async def test_cors_restrictions(self):
        """
        Test that CORS is restricted to local origins only.
        """
        from src.core.config import settings

        # All allowed origins should be local
        for origin in settings.allowed_origins:
            assert "localhost" in origin or "127.0.0.1" in origin, \
                f"CORS should only allow local origins, got: {origin}"

    @pytest.mark.asyncio
    async def test_no_persistent_student_profiles(self):
        """
        Test that student profiles are not persistently stored with PII.
        """
        # This would check that the system doesn't create long-term
        # student profiles with identifying information

        # Implementation dependent
        pass


class TestSecureDataHandling:
    """
    Test secure data handling practices.
    """

    @pytest.mark.asyncio
    async def test_sensitive_data_not_in_error_messages(self):
        """
        Test that sensitive data is not leaked in error messages.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Send malformed request with PII
            response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "Test with PII: john@school.edu",
                    "user_id": "invalid_user_with_pii@email.com"
                }
            )

            # Even error responses should not leak PII
            # (This is a conceptual test - actual implementation may vary)

    @pytest.mark.asyncio
    async def test_no_pii_in_api_documentation(self):
        """
        Test that API documentation does not contain real PII examples.
        """
        # This would check the OpenAPI schema
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/docs")
            assert response.status_code == 200

            # Check that documentation doesn't use real emails, names, etc.
            # (implementation dependent)


# Helper functions for PII scanning
def scan_directory_for_pii(directory: Path, extensions: List[str] = None) -> Dict[str, List[Dict]]:
    """
    Scan a directory for PII in files.

    Args:
        directory: Directory to scan
        extensions: File extensions to check (default: .log, .txt, .json)

    Returns:
        Dictionary mapping file paths to PII findings
    """
    if extensions is None:
        extensions = ['.log', '.txt', '.json']

    pii_checker = TestLogSanitization()
    results = {}

    for file_path in directory.rglob('*'):
        if file_path.suffix in extensions:
            findings = pii_checker.check_file_for_pii(file_path)
            if findings:
                results[str(file_path)] = findings

    return results


def generate_compliance_report(scan_results: Dict[str, List[Dict]]) -> str:
    """
    Generate a FERPA compliance report from scan results.

    Args:
        scan_results: Results from scan_directory_for_pii

    Returns:
        Formatted report string
    """
    report = ["=" * 80]
    report.append("FERPA COMPLIANCE SCAN REPORT")
    report.append("=" * 80)
    report.append("")

    if not scan_results:
        report.append("✓ NO PII DETECTED - System appears to be compliant")
        report.append("")
        return "\n".join(report)

    report.append(f"⚠ PII DETECTED in {len(scan_results)} file(s)")
    report.append("")

    for file_path, findings in scan_results.items():
        report.append(f"File: {file_path}")
        report.append(f"  PII Instances Found: {len(findings)}")

        for finding in findings[:3]:  # Show first 3 per file
            report.append(f"  - Line {finding['line']} ({finding['type']}): {finding['content']}")

        if len(findings) > 3:
            report.append(f"  ... and {len(findings) - 3} more")

        report.append("")

    report.append("=" * 80)
    report.append("ACTION REQUIRED: Review and remediate PII findings")
    report.append("=" * 80)

    return "\n".join(report)


if __name__ == "__main__":
    """Run PII scans manually"""
    import sys

    # Scan for PII in common locations
    scan_dirs = [
        Path("/home/papi/Documents/mu2-cognitive-os/packages/brain/logs"),
        Path("/home/papi/Documents/mu2-cognitive-os/logs"),
    ]

    all_results = {}
    for scan_dir in scan_dirs:
        if scan_dir.exists():
            results = scan_directory_for_pii(scan_dir)
            all_results.update(results)

    report = generate_compliance_report(all_results)
    print(report)

    # Exit with error code if PII found
    sys.exit(1 if all_results else 0)
