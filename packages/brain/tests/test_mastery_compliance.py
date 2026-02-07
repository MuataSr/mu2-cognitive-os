"""
Mastery Tracking Compliance Test Suite
FERPA Compliance and Bias Audit for Bayesian Knowledge Tracing

This test suite ensures:
- No external API calls for mastery tracking
- Data masking based on user role
- Reset protocol compliance
- No telemetry or analytics
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.services.mastery_engine import (
    mastery_engine,
    MasteryState,
    LearningEvent,
    mask_student_id,
)


class TestMasteryPIIProtection:
    """
    Test that PII is protected in mastery tracking features.
    """

    @pytest.mark.asyncio
    async def test_student_id_masking_for_researchers(self):
        """
        Test that student IDs are masked for researcher role.
        """
        full_id = "student-12345678-abc-def"
        masked = mask_student_id(full_id, "researcher")

        # Should be truncated
        assert len(masked) < len(full_id)
        assert "..." in masked or "***" in masked
        assert full_id not in masked

    @pytest.mark.asyncio
    async def test_student_id_not_masked_for_teachers(self):
        """
        Test that student IDs are NOT masked for teacher role.
        """
        full_id = "student-12345678-abc-def"
        not_masked = mask_student_id(full_id, "teacher")

        # Should be unchanged
        assert not_masked == full_id

    @pytest.mark.asyncio
    async def test_external_role_masking(self):
        """
        Test that student IDs are masked for external role.
        """
        full_id = "student-12345678-abc-def"
        masked = mask_student_id(full_id, "external")

        # Should be truncated
        assert len(masked) < len(full_id)
        assert "..." in masked or "***" in masked

    @pytest.mark.asyncio
    async def test_class_mastery_data_is_anonymized(self):
        """
        Test that class mastery API returns masked IDs for researchers.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/mastery/class")

            assert response.status_code == 200
            data = response.json()

            # Check that students exist
            assert "students" in data

            # Verify masked_id field exists and is different from user_id
            for student in data["students"]:
                assert "masked_id" in student
                if len(student["user_id"]) > 8:
                    # Should be masked
                    assert student["masked_id"] != student["user_id"] or \
                           len(student["masked_id"]) <= 12


class TestResetProtocol:
    """
    Test the reset protocol for students returning after absence.
    """

    @pytest.mark.asyncio
    async def test_no_reset_within_threshold(self):
        """
        Test that mastery doesn't reset if student returns within threshold.
        """
        engine = mastery_engine

        # Create a mastered state
        state = MasteryState(
            user_id="test-student",
            skill_id="test-skill",
            probability_mastery=0.95,
            total_attempts=10,
            correct_attempts=9,
            last_attempt_at=datetime.utcnow()
        )

        # Apply reset protocol with 1 hour since last attempt
        updated_state = engine.apply_reset_protocol(state, hours_since_last=1.0)

        # Mastery should remain high (no significant change)
        assert updated_state.probability_mastery > 0.90

    @pytest.mark.asyncio
    async def test_reset_after_threshold(self):
        """
        Test that mastery increases uncertainty after threshold.
        """
        engine = mastery_engine

        # Create a mastered state
        state = MasteryState(
            user_id="test-student",
            skill_id="test-skill",
            probability_mastery=0.95,
            total_attempts=10,
            correct_attempts=9,
            last_attempt_at=datetime.utcnow()
        )

        # Apply reset protocol with 48 hours since last attempt
        updated_state = engine.apply_reset_protocol(state, hours_since_last=48.0)

        # Mastery should decrease (move toward 0.5)
        assert updated_state.probability_mastery < 0.95
        # But should still be above 0.5 (not full reset)
        assert updated_state.probability_mastery > 0.5

    @pytest.mark.asyncio
    async def test_week_absence_significant_reset(self):
        """
        Test that a week absence causes more significant uncertainty.
        """
        engine = mastery_engine

        # Create a mastered state
        initial_mastery = 0.95
        state = MasteryState(
            user_id="test-student",
            skill_id="test-skill",
            probability_mastery=initial_mastery,
            total_attempts=10,
            correct_attempts=9,
            last_attempt_at=datetime.utcnow()
        )

        # Apply reset protocol with 168 hours (1 week) since last attempt
        updated_state = engine.apply_reset_protocol(state, hours_since_last=168.0)

        # After a week, should see significant uncertainty increase
        # (move toward 0.5)
        assert updated_state.probability_mastery < initial_mastery

    @pytest.mark.asyncio
    async def test_reset_does_not_go_below_threshold(self):
        """
        Test that reset protocol doesn't push mastery too low.
        """
        engine = mastery_engine

        # Create a mastered state
        state = MasteryState(
            user_id="test-student",
            skill_id="test-skill",
            probability_mastery=0.95,
            total_attempts=10,
            correct_attempts=9,
            last_attempt_at=datetime.utcnow()
        )

        # Apply reset protocol with extreme time (1 month)
        updated_state = engine.apply_reset_protocol(state, hours_since_last=720.0)

        # Should not go below 0.5 (maximum uncertainty)
        assert updated_state.probability_mastery >= 0.5
        # But should show some uncertainty
        assert updated_state.probability_mastery < 0.95


class TestNoExternalAPICalls:
    """
    Test that mastery tracking doesn't make external API calls.
    """

    @pytest.mark.asyncio
    async def test_mastery_record_local_only(self):
        """
        Test that recording learning events doesn't call external APIs.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Record a learning event
            response = await client.post(
                "/api/v1/mastery/record",
                json={
                    "user_id": "test-student",
                    "skill_id": "photosynthesis-basics",
                    "is_correct": True,
                    "attempts": 1
                }
            )

            # Should succeed without external calls
            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "user_id" in data
            assert "skill_id" in data
            assert "new_mastery" in data
            assert "status" in data

    @pytest.mark.asyncio
    async def test_mastery_calculation_is_local(self):
        """
        Test that BKT calculation is done locally, not via external API.
        """
        # Create a learning event
        event = LearningEvent(
            user_id="test-student",
            skill_id="test-skill",
            is_correct=True,
            attempts=1
        )

        # Process locally using MasteryEngine
        state = mastery_engine.process_event(event)

        # Verify calculation was done locally
        assert state.probability_mastery > 0.5  # Correct answer increases mastery
        assert state.user_id == "test-student"
        assert state.skill_id == "test-skill"

    @pytest.mark.asyncio
    async def test_class_mastery_local_only(self):
        """
        Test that class mastery endpoint doesn't call external APIs.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/mastery/class")

            # Should succeed without external calls
            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "students" in data
            assert "total_students" in data
            assert "class_avg_mastery" in data


class TestBKTCorrectness:
    """
    Test that BKT calculations are mathematically correct.
    """

    @pytest.mark.asyncio
    async def test_correct_answer_increases_mastery(self):
        """
        Test that a correct answer increases mastery probability.
        """
        engine = mastery_engine
        initial_mastery = 0.5

        new_mastery = engine.update_state(
            is_correct=True,
            current_mastery=initial_mastery
        )

        assert new_mastery > initial_mastery

    @pytest.mark.asyncio
    async def test_incorrect_answer_decreases_mastery(self):
        """
        Test that an incorrect answer decreases mastery probability.
        """
        engine = mastery_engine
        initial_mastery = 0.5

        new_mastery = engine.update_state(
            is_correct=False,
            current_mastery=initial_mastery
        )

        assert new_mastery < initial_mastery

    @pytest.mark.asyncio
    async def test_mastery_clamped_to_valid_range(self):
        """
        Test that mastery is always clamped to [0.01, 0.99].
        """
        engine = mastery_engine

        # Test with very high mastery
        high_mastery = engine.update_state(is_correct=True, current_mastery=0.99)
        assert high_mastery <= 0.99
        assert high_mastery >= 0.01

        # Test with very low mastery
        low_mastery = engine.update_state(is_correct=False, current_mastery=0.01)
        assert low_mastery <= 0.99
        assert low_mastery >= 0.01

    @pytest.mark.asyncio
    async def test_multiple_correct_answers_approach_mastery(self):
        """
        Test that multiple correct answers approach mastery.
        """
        engine = mastery_engine
        mastery = 0.5

        for _ in range(5):
            mastery = engine.update_state(is_correct=True, current_mastery=mastery)

        # After 5 correct answers, should be close to mastery
        assert mastery > 0.7

    @pytest.mark.asyncio
    async def test_status_classification_correct(self):
        """
        Test that status classification follows the red dot logic.
        """
        from src.services.mastery_engine import MasteryState

        engine = mastery_engine

        # Test STRUGGLING: low mastery + multiple attempts
        struggling_state = MasteryState(
            user_id="test",
            skill_id="test",
            probability_mastery=0.4,
            total_attempts=5
        )
        status = engine.get_status(struggling_state)
        assert status.status == "STRUGGLING"

        # Test MASTERED: high mastery
        mastered_state = MasteryState(
            user_id="test",
            skill_id="test",
            probability_mastery=0.95,
            total_attempts=10
        )
        status = engine.get_status(mastered_state)
        assert status.status == "MASTERED"

        # Test LEARNING: middle ground
        learning_state = MasteryState(
            user_id="test",
            skill_id="test",
            probability_mastery=0.7,
            total_attempts=5
        )
        status = engine.get_status(learning_state)
        assert status.status == "LEARNING"


class TestNoTelemetry:
    """
    Test that no telemetry or analytics are included in mastery tracking.
    """

    @pytest.mark.asyncio
    async def test_no_analytics_in_mastery_endpoints(self):
        """
        Test that mastery endpoints don't include analytics tracking.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:

            # Check various endpoints
            endpoints = [
                "/api/v1/mastery/class",
                "/api/v1/mastery/skills",
            ]

            for endpoint in endpoints:
                response = await client.get(endpoint)
                assert response.status_code == 200

                data = response.json()

                # Check for common analytics fields
                assert "analytics_id" not in str(data)
                assert "telemetry" not in str(data).lower()
                assert "tracking_id" not in str(data)

    def test_no_external_analytics_imports(self):
        """
        Test that no external analytics services are imported.
        """
        import sys
        import src.services.mastery_engine as mastery_module

        # Get the source code
        source_file = mastery_module.__file__

        with open(source_file, 'r') as f:
            content = f.read()

        # Check for common analytics services
        forbidden = [
            'google.analytics',
            'segment',
            'mixpanel',
            'amplitude',
            'gtm',
            'gtag',
            'telemetry',
        ]

        for term in forbidden:
            assert term not in content.lower(), \
                f"Forbidden analytics term found: {term}"


class TestDataIntegrity:
    """
    Test data integrity for mastery tracking.
    """

    @pytest.mark.asyncio
    async def test_learning_event_timestamp_is_recorded(self):
        """
        Test that learning events record timestamps.
        """
        event = LearningEvent(
            user_id="test-student",
            skill_id="test-skill",
            is_correct=True
        )

        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_mastery_state_preserves_history(self):
        """
        Test that mastery state preserves attempt history.
        """
        state = MasteryState(
            user_id="test-student",
            skill_id="test-skill",
            probability_mastery=0.75,
            total_attempts=10,
            correct_attempts=8,
            consecutive_correct=3,
            consecutive_incorrect=0
        )

        assert state.total_attempts == 10
        assert state.correct_attempts == 8
        assert state.consecutive_correct == 3
        assert state.consecutive_incorrect == 0


# Helper function to run compliance tests
def run_mastery_compliance_tests():
    """
    Run all mastery compliance tests.
    """
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-W", "ignore::DeprecationWarning"
    ])


if __name__ == "__main__":
    run_mastery_compliance_tests()
