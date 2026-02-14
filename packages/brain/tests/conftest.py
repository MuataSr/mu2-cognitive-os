"""
Pytest Configuration and Fixtures - Mu2 Cognitive OS
=================================================

Shared fixtures for behavioral detector tests.
"""

import pytest
from datetime import datetime, timedelta
from src.services.behavioral_detector import (
    BehavioralDetector,
    EventType,
    UrgencyLevel,
    LearningEvent,
    ClickEvent,
    BehavioralSignal,
)


@pytest.fixture
def detector():
    """Fresh detector instance for each test"""
    return BehavioralDetector()


@pytest.fixture
def sample_user_id():
    """Test user ID"""
    return "test-student-123"


@pytest.fixture
def correct_learning_events(sample_user_id):
    """Series of correct answers"""
    return [
        LearningEvent(
            user_id=sample_user_id,
            skill_id="photosynthesis",
            is_correct=True,
            attempts=1,
            time_spent_seconds=30,
            timestamp=datetime.utcnow()
        )
        for i in range(5)
    ]


@pytest.fixture
def incorrect_learning_events(sample_user_id):
    """Series of incorrect answers"""
    return [
        LearningEvent(
            user_id=sample_user_id,
            skill_id="photosynthesis",
            is_correct=False,
            attempts=2,
            time_spent_seconds=45,
            timestamp=datetime.utcnow() - timedelta(seconds=i*60)
        )
        for i in range(5)
    ]


@pytest.fixture
def mixed_learning_events(sample_user_id):
    """Mix of correct and incorrect"""
    events = []
    for i in range(10):
        events.append(LearningEvent(
            user_id=sample_user_id,
            skill_id="photosynthesis",
            is_correct=(i % 2 == 0),
            attempts=1 + (i % 3),
            time_spent_seconds=30 + (i * 10),
            timestamp=datetime.utcnow() - timedelta(seconds=i*30)
        ))
    return events


@pytest.fixture
def normal_clickstream(sample_user_id):
    """Normal clicking pattern"""
    base_time = datetime.utcnow()
    # Create events in chronological order (oldest first, newest last)
    return [
        ClickEvent(
            user_id=sample_user_id,
            x=100 + (i * 50),
            y=200 + (i * 30),
            element_id=f"element-{i}",
            timestamp=base_time - timedelta(seconds=(9-i)*2)  # Reverse order: event 0 is oldest
        )
        for i in range(10)
    ]


@pytest.fixture
def rapid_clickstream(sample_user_id):
    """Rapid clicking pattern (frustration)"""
    base_time = datetime.utcnow()
    return [
        ClickEvent(
            user_id=sample_user_id,
            x=100,
            y=200,
            element_id=f"button-{i}",
            timestamp=base_time - timedelta(milliseconds=i*200)
        )
        for i in range(5)
    ]


@pytest.fixture
def diverse_clickstream(sample_user_id):
    """Diverse interaction pattern (engagement)"""
    base_time = datetime.utcnow()
    elements = ["submit", "next", "help", "settings", "textbook"]
    return [
        ClickEvent(
            user_id=sample_user_id,
            x=100 + (i * 80),
            y=150 + (i * 40),
            element_id=elements[i % len(elements)],
            timestamp=base_time - timedelta(seconds=i*3)
        )
        for i in range(10)
    ]
