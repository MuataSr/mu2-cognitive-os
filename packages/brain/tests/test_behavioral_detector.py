"""
Behavioral Detector Tests - Mu2 Cognitive OS
========================================

Tests for behavioral detection service that drives the Chameleon Engine.

Run with:
    pytest tests/test_behavioral_detector.py -v
"""

import pytest
from datetime import datetime, timedelta
from src.services.behavioral_detector import (
    behavioral_detector,
    EventType,
    UrgencyLevel,
    LearningEvent,
    ClickEvent,
    BehavioralSignal,
)


# Fixtures are now in conftest.py for sharing across test classes


class TestFrustrationDetection:
    """Tests for frustration detection"""

    @pytest.mark.asyncio
    async def test_three_consecutive_errors_trigger_frustration(self, detector, sample_user_id, incorrect_learning_events):
        """3+ consecutive errors should trigger frustration detection"""
        # Act
        is_frustrated, confidence, reasoning = await detector.detect_frustration(
            user_id=sample_user_id,
            learning_events=incorrect_learning_events
        )

        # Assert
        assert is_frustrated is True
        assert confidence >= 0.5
        assert any("consecutive" in r.lower() for r in reasoning)

    @pytest.mark.asyncio
    async def test_all_correct_no_frustration(self, detector, sample_user_id, correct_learning_events):
        """All correct answers should not trigger frustration"""
        # Act
        is_frustrated, confidence, reasoning = await detector.detect_frustration(
            user_id=sample_user_id,
            learning_events=correct_learning_events
        )

        # Assert
        assert is_frustrated is False
        assert confidence < 0.3

    @pytest.mark.asyncio
    async def test_rapid_failures_detected(self, detector, sample_user_id):
        """Rapid incorrect attempts (<10s) should be detected"""
        events = []
        now = datetime.utcnow()

        # Add 3 rapid failures
        for i in range(3):
            events.append(LearningEvent(
                user_id=sample_user_id,
                skill_id="photosynthesis",
                is_correct=False,
                attempts=1,
                time_spent_seconds=5,
                timestamp=now - timedelta(seconds=i*6)
            ))

        # Act
        is_frustrated, confidence, reasoning = await detector.detect_frustration(
            user_id=sample_user_id,
            learning_events=events
        )

        # Assert
        assert is_frustrated is True
        assert any("rapid" in r.lower() for r in reasoning)

    @pytest.mark.asyncio
    async def test_long_struggles_detected(self, detector, sample_user_id):
        """Long struggles (>2min) should be detected"""
        events = []
        now = datetime.utcnow()

        # Add 2 long struggles
        for i in range(2):
            events.append(LearningEvent(
                user_id=sample_user_id,
                skill_id="cellular-respiration",
                is_correct=False,
                attempts=3,
                time_spent_seconds=150,
                timestamp=now - timedelta(minutes=i*3)
            ))

        # Act
        is_frustrated, confidence, reasoning = await detector.detect_frustration(
            user_id=sample_user_id,
            learning_events=events
        )

        # Assert
        assert is_frustrated is True
        assert confidence >= 0.5
        assert any("struggle" in r.lower() for r in reasoning)


class TestEngagementDetection:
    """Tests for engagement detection"""

    @pytest.mark.asyncio
    async def test_healthy_click_rate_detected_as_engaged(self, detector, sample_user_id, normal_clickstream):
        """5-30 clicks per minute should indicate engagement"""
        # Arrange
        events = normal_clickstream
        time_on_task = 120  # 2 minutes

        # Act
        is_engaged, confidence, reasoning = await detector.detect_engagement(
            user_id=sample_user_id,
            clickstream=events,
            time_on_task=time_on_task
        )

        # Assert
        assert is_engaged is True
        assert confidence >= 0.4
        assert any("engaged" in r.lower() or "healthy" in r.lower() for r in reasoning)

    @pytest.mark.asyncio
    async def test_very_high_click_rate_indicates_frustration(self, detector, sample_user_id, rapid_clickstream):
        """50+ clicks per minute should indicate frustration"""
        # Arrange
        events = rapid_clickstream
        time_on_task = 60

        # Act
        is_engaged, confidence, reasoning = await detector.detect_engagement(
            user_id=sample_user_id,
            clickstream=events,
            time_on_task=time_on_task
        )

        # Assert - high click rate should lower confidence
        assert is_engaged is False or confidence < 0.3
        assert any("high" in r.lower() or "rapid" in r.lower() for r in reasoning)

    @pytest.mark.asyncio
    async def test_diverse_elements_detected_as_engaged(self, detector, sample_user_id, diverse_clickstream):
        """Interacting with 3+ different elements indicates engagement"""
        # Arrange
        time_on_task = 90

        # Act
        is_engaged, confidence, reasoning = await detector.detect_engagement(
            user_id=sample_user_id,
            clickstream=diverse_clickstream,
            time_on_task=time_on_task
        )

        # Assert
        assert is_engaged is True
        assert confidence >= 0.4
        assert any("diverse" in r.lower() for r in reasoning)

    @pytest.mark.asyncio
    async def test_no_clickstream_returns_low_confidence(self, detector, sample_user_id):
        """No click data should return low confidence engagement"""
        # Act
        is_engaged, confidence, reasoning = await detector.detect_engagement(
            user_id=sample_user_id,
            clickstream=[],
            time_on_task=60
        )

        # Assert
        assert is_engaged is False
        assert confidence < 0.3


class TestStrugglingDetection:
    """Tests for struggling detection"""

    @pytest.mark.asyncio
    async def test_long_time_on_task_indicates_struggling(self, detector, sample_user_id):
        """>2min on task should indicate struggling"""
        events = []
        now = datetime.utcnow()

        # Add a long task
        events.append(LearningEvent(
            user_id=sample_user_id,
            skill_id="mitosis-stages",
            is_correct=False,
            attempts=5,
            time_spent_seconds=180,  # 3 minutes
            timestamp=now - timedelta(minutes=3)
        ))

        # Act
        is_struggling, confidence, reasoning = await detector.detect_struggling(
            user_id=sample_user_id,
            learning_events=events,
            time_on_task=180
        )

        # Assert
        assert is_struggling is True
        assert confidence >= 0.5
        assert any("struggle" in r.lower() or "long" in r.lower() for r in reasoning)

    @pytest.mark.asyncio
    async def test_retry_loop_detected(self, detector, sample_user_id):
        """3+ attempts on same skill should indicate struggle"""
        events = []
        now = datetime.utcnow()

        # Add retry loop
        for i in range(4):
            events.append(LearningEvent(
                user_id=sample_user_id,
                skill_id="protein-synthesis",
                is_correct=(i == 3),  # Only last one correct
                attempts=1,
                time_spent_seconds=30,
                timestamp=now - timedelta(seconds=i*20)
            ))

        # Act
        is_struggling, confidence, reasoning = await detector.detect_struggling(
            user_id=sample_user_id,
            learning_events=events,
            time_on_task=120  # Total time
        )

        # Assert
        assert is_struggling is True
        assert confidence >= 0.5
        assert any("retry" in r.lower() or "loop" in r.lower() for r in reasoning)


class TestRapidClickingDetection:
    """Tests for rapid clicking (frustration signal)"""

    @pytest.mark.asyncio
    async def test_five_clicks_in_two_seconds_is_rapid(self, detector, sample_user_id):
        """5 clicks within 2 seconds should be rapid clicking"""
        # Arrange
        base_time = datetime.utcnow()
        events = [
            ClickEvent(
                user_id=sample_user_id,
                x=100,
                y=200,
                timestamp=base_time - timedelta(milliseconds=i*400)
            )
            for i in range(5)
        ]

        # Act
        is_rapid, confidence = await detector.detect_rapid_clicking(
            user_id=sample_user_id,
            clickstream=events
        )

        # Assert
        assert is_rapid is True
        assert confidence >= 0.7

    @pytest.mark.asyncio
    async def test_slow_clicks_not_rapid(self, detector, sample_user_id):
        """Clicks spread out should not be rapid"""
        # Arrange
        base_time = datetime.utcnow()
        events = [
            ClickEvent(
                user_id=sample_user_id,
                x=100,
                y=200,
                timestamp=base_time - timedelta(seconds=i*3)
            )
            for i in range(5)
        ]

        # Act
        is_rapid, confidence = await detector.detect_rapid_clicking(
            user_id=sample_user_id,
            clickstream=events
        )

        # Assert
        assert is_rapid is False
        assert confidence < 0.3


class TestModeSuggestion:
    """Tests for UI mode suggestion logic"""

    @pytest.mark.asyncio
    async def test_frustration_with_errors_suggests_high_contrast_focus(self, detector, sample_user_id):
        """Frustration + 3+ errors should suggest high_contrast_focus"""
        # Arrange
        events = []
        for i in range(3):
            events.append(LearningEvent(
                user_id=sample_user_id,
                skill_id="test",
                is_correct=False,
                attempts=2,
                time_spent_seconds=60,
                timestamp=datetime.utcnow()
            ))

        # Act - analyze with frustration signals
        signals = await detector.analyze_behavioral_signals(
            user_id=sample_user_id,
            learning_events=events,
            clickstream=[],
            time_on_task_seconds=60
        )

        # Assert
        assert signals.suggested_mode == "high_contrast_focus"
        assert signals.urgency == UrgencyLevel.INTERVENTION

    @pytest.mark.asyncio
    async def test_struggling_suggests_focus_mode(self, detector, sample_user_id):
        """Struggling without high errors should suggest focus"""
        # Arrange
        events = [
            LearningEvent(
                user_id=sample_user_id,
                skill_id="test",
                is_correct=False,
                attempts=1,
                time_spent_seconds=150,
                timestamp=datetime.utcnow()
            )
        ]

        # Act
        signals = await detector.analyze_behavioral_signals(
            user_id=sample_user_id,
            learning_events=events,
            clickstream=[],
            time_on_task_seconds=150
        )

        # Assert
        assert signals.suggested_mode == "focus"
        assert signals.urgency == UrgencyLevel.ATTENTION

    @pytest.mark.asyncio
    async def test_engaged_user_stays_in_standard_mode(self, detector, sample_user_id, correct_learning_events):
        """Engaged user should stay in standard mode"""
        # Arrange
        events = correct_learning_events[:3]

        # Act - need to create clickstream fixture reference
        base_time = datetime.utcnow()
        clickstream = [
            ClickEvent(
                user_id=sample_user_id,
                x=100 + (i * 50),
                y=200 + (i * 30),
                element_id=f"element-{i}",
                timestamp=base_time - timedelta(seconds=i*2)
            )
            for i in range(3)
        ]

        signals = await detector.analyze_behavioral_signals(
            user_id=sample_user_id,
            learning_events=events,
            clickstream=clickstream,
            time_on_task_seconds=90
        )

        # Assert
        assert signals.suggested_mode == "standard"
        assert signals.urgency == UrgencyLevel.NONE
        assert signals.is_engaged is True

    @pytest.mark.asyncio
    async def test_no_signals_defaults_to_standard_mode(self, detector, sample_user_id):
        """No behavioral signals should default to standard mode"""
        # Act
        signals = await detector.analyze_behavioral_signals(
            user_id=sample_user_id,
            learning_events=[],
            clickstream=[],
            time_on_task_seconds=60
        )

        # Assert
        assert signals.suggested_mode == "standard"
        assert signals.confidence < 0.3


class TestBehavioralSignalAggregation:
    """Tests for complete behavioral signal analysis"""

    @pytest.mark.asyncio
    async def test_complete_signal_analysis(self, detector, sample_user_id, incorrect_learning_events):
        """Test full signal analysis with frustration pattern"""
        # Arrange
        base_time = datetime.utcnow()
        clickstream = [
            ClickEvent(
                user_id=sample_user_id,
                x=100,
                y=200,
                element_id="submit",
                timestamp=base_time - timedelta(seconds=i*5)
            )
            for i in range(8)
        ]

        # Act
        signals = await detector.analyze_behavioral_signals(
            user_id=sample_user_id,
            learning_events=incorrect_learning_events,
            clickstream=clickstream,
            time_on_task_seconds=180
        )

        # Assert - should detect frustration and struggling
        assert signals.is_frustrated is True
        assert signals.is_struggling is True
        assert signals.consecutive_errors >= 3
        assert signals.urgency == UrgencyLevel.INTERVENTION
        assert signals.suggested_mode == "high_contrast_focus"
        assert len(signals.reasoning) > 0  # Should have multiple reasons

    @pytest.mark.asyncio
    async def test_signal_confidence_calculation(self, detector, sample_user_id):
        """Confidence should be max of individual signal confidences"""
        # Arrange - create events that trigger multiple signals
        events = []
        now = datetime.utcnow()

        for i in range(3):
            events.append(LearningEvent(
                user_id=sample_user_id,
                skill_id="test",
                is_correct=False,
                attempts=3,
                time_spent_seconds=180,
                timestamp=now - timedelta(seconds=i*10)
            ))

        clickstream = [
            ClickEvent(user_id=sample_user_id, x=100, y=200, timestamp=datetime.utcnow())
            for _ in range(3)
        ]

        # Act
        signals = await detector.analyze_behavioral_signals(
            user_id=sample_user_id,
            learning_events=events,
            clickstream=clickstream,
            time_on_task_seconds=180
        )

        # Assert - confidence should reflect combined signals
        assert signals.confidence >= 0.5  # Multiple signals detected
        assert signals.is_frustrated is True
