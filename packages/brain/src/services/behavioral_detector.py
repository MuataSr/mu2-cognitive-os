"""
Behavioral Detector Service - Mu2 Cognitive OS
==============================================

Detects behavioral signals that trigger adaptive UI changes.

This is the "sensor" layer of the Chameleon Engine:
- Detects frustration (3+ consecutive errors)
- Detects engagement (time + clickstream)
- Detects abandonment (long inactivity)
- Suggests UI mode changes

FERPA Compliance:
- All behavioral data stays local
- No PII in behavioral signals
- User IDs are anonymized
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum


class EventType(str, Enum):
    """Types of behavioral events"""
    SQUINTING = "squinting"
    FRUSTRATION = "frustration"
    ENGAGEMENT = "engagement"
    ABANDONMENT = "abandonment"
    RAPID_CLICKING = "rapid_clicking"
    LONG_PAUSE = "long_pause"
    CONSECUTIVE_ERRORS = "consecutive_errors"


class UrgencyLevel(str, Enum):
    """Urgency of intervention needed"""
    NONE = "none"
    ATTENTION = "attention"
    INTERVENTION = "intervention"


class BehavioralEvent(BaseModel):
    """A detected behavioral event"""
    event_type: EventType
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BehavioralSignal(BaseModel):
    """Aggregated behavioral signals for UI decision making"""
    user_id: str
    is_frustrated: bool
    is_engaged: bool
    is_struggling: bool
    consecutive_errors: int
    time_on_task_seconds: int
    last_activity_seconds_ago: int
    suggested_mode: Literal["standard", "focus", "high_contrast_focus", "exploration"]
    urgency: UrgencyLevel
    confidence: float
    reasoning: List[str]


class ClickEvent(BaseModel):
    """A click/cursor event"""
    user_id: str
    x: int
    y: int
    timestamp: datetime
    element_id: Optional[str] = None


class LearningEvent(BaseModel):
    """A learning/quiz event"""
    user_id: str
    skill_id: str
    is_correct: bool
    attempts: int
    time_spent_seconds: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BehavioralDetector:
    """
    Detects behavioral signals for adaptive UI triggering

    Inputs:
    1. Mouse movements (jittery = frustration)
    2. Time per question (>2min = struggling)
    3. Consecutive errors (3+ = intervention needed)
    4. Clickstream patterns (rapid clicking = frustration)
    """

    # Thresholds for detection
    FRUSTRATION_ERROR_THRESHOLD = 3  # Consecutive errors
    STRUGGLING_TIME_THRESHOLD = 120  # 2 minutes
    RAPID_CLICK_THRESHOLD = 5  # Clicks in 2 seconds
    ABANDONMENT_THRESHOLD = 300  # 5 minutes inactivity

    def __init__(self):
        """Initialize the behavioral detector"""
        # In-memory store for recent events (in production, use Redis)
        self._click_events: Dict[str, List[ClickEvent]] = {}
        self._learning_events: Dict[str, List[LearningEvent]] = {}
        self._consecutive_errors: Dict[str, int] = {}

    async def detect_frustration(
        self,
        user_id: str,
        learning_events: List[LearningEvent]
    ) -> tuple[bool, float, List[str]]:
        """
        Detect if user is frustrated based on learning events

        Returns:
            (is_frustrated, confidence, reasoning)
        """
        reasoning = []
        confidence = 0.0
        error_count = 0

        # Check consecutive errors
        recent_events = learning_events[-10:] if learning_events else []
        for event in reversed(recent_events):
            if not event.is_correct:
                error_count += 1
            else:
                break

        if error_count >= self.FRUSTRATION_ERROR_THRESHOLD:
            reasoning.append(f"{error_count} consecutive errors detected")
            confidence += 0.5  # 3+ errors alone triggers frustration

        # Check for rapid incorrect attempts
        rapid_failures = 0
        for event in recent_events[-5:]:
            if not event.is_correct and event.time_spent_seconds < 10:
                rapid_failures += 1

        if rapid_failures >= 3:
            reasoning.append(f"{rapid_failures} rapid failures (<10s each)")
            confidence += 0.3

        # Check time spent on incorrect answers
        long_struggles = sum(
            1 for e in recent_events
            if not e.is_correct and e.time_spent_seconds > self.STRUGGLING_TIME_THRESHOLD
        )

        if long_struggles > 0:
            reasoning.append(f"{long_struggles} long struggles (>2min)")
            confidence += 0.3

        is_frustrated = confidence >= 0.5
        return is_frustrated, min(confidence, 1.0), reasoning

    async def detect_engagement(
        self,
        user_id: str,
        clickstream: List[ClickEvent],
        time_on_task: int
    ) -> tuple[bool, float, List[str]]:
        """
        Detect if user is engaged

        Returns:
            (is_engaged, confidence, reasoning)
        """
        reasoning = []
        confidence = 0.0

        # Check click frequency
        is_rapid_clicking = False  # Flag for very high click rates
        if clickstream:
            # Calculate clicks per minute
            time_span = (clickstream[-1].timestamp - clickstream[0].timestamp).total_seconds()
            if time_span > 0:
                clicks_per_minute = (len(clickstream) / time_span) * 60
                if 5 <= clicks_per_minute <= 30:  # Sweet spot for engagement
                    reasoning.append(f"Healthy click rate: {clicks_per_minute:.1f}/min")
                    confidence += 0.3
                elif clicks_per_minute > 50:
                    reasoning.append(f"Very high click rate: {clicks_per_minute:.1f}/min (indicates frustration)")
                    confidence = 0.0  # High click rate = NOT engaged
                    is_rapid_clicking = True

        # Skip other engagement checks if rapid clicking detected
        if is_rapid_clicking:
            is_engaged = False
            return is_engaged, confidence, reasoning

        # Check time on task
        if 30 <= time_on_task <= 600:  # 30s to 10min is good engagement
            reasoning.append(f"Good time on task: {time_on_task}s")
            confidence += 0.4
        elif time_on_task > 600:
            reasoning.append(f"Long time on task: {time_on_task}s (may indicate struggle)")
            confidence -= 0.2

        # Check for variety of interactions (not clicking same element)
        if clickstream:
            unique_elements = len(set(e.element_id for e in clickstream if e.element_id))
            if unique_elements >= 3:
                reasoning.append(f"Diverse interactions: {unique_elements} different elements")
                confidence += 0.3

        is_engaged = confidence >= 0.4
        return is_engaged, max(0.0, min(confidence, 1.0)), reasoning

    async def detect_struggling(
        self,
        user_id: str,
        learning_events: List[LearningEvent],
        time_on_task: int
    ) -> tuple[bool, float, List[str]]:
        """
        Detect if user is struggling (needs intervention)

        Returns:
            (is_struggling, confidence, reasoning)
        """
        reasoning = []
        confidence = 0.0

        # Check consecutive errors
        recent_events = learning_events[-5:] if learning_events else []
        error_count = sum(1 for e in recent_events if not e.is_correct)

        if error_count >= 3:
            reasoning.append(f"{error_count}/5 recent attempts incorrect")
            confidence += 0.4

        # Check time on task
        if time_on_task > self.STRUGGLING_TIME_THRESHOLD:
            reasoning.append(f"Long time on task: {time_on_task}s")
            confidence += 0.5  # >2min alone triggers struggling

        # Check if retrying same skill multiple times
        if recent_events:
            skill_attempts = {}
            for event in recent_events:
                skill_attempts[event.skill_id] = skill_attempts.get(event.skill_id, 0) + 1

            for skill, attempts in skill_attempts.items():
                if attempts >= 3:
                    reasoning.append(f"Retry loop on {skill}: {attempts} attempts")
                    confidence += 0.3

        is_struggling = confidence >= 0.5
        return is_struggling, min(confidence, 1.0), reasoning

    async def detect_rapid_clicking(
        self,
        user_id: str,
        clickstream: List[ClickEvent]
    ) -> tuple[bool, float]:
        """
        Detect rapid clicking behavior (sign of frustration)

        Returns:
            (is_rapid_clicking, confidence)
        """
        if not clickstream or len(clickstream) < self.RAPID_CLICK_THRESHOLD:
            return False, 0.0

        # Check if last N clicks happened within 2 seconds
        recent_clicks = clickstream[-self.RAPID_CLICK_THRESHOLD:]
        time_span = (recent_clicks[-1].timestamp - recent_clicks[0].timestamp).total_seconds()

        if time_span <= 2.0:
            confidence = 0.7 + (0.3 * (1 - time_span / 2.0))  # Higher confidence for faster clicking
            return True, min(confidence, 1.0)

        return False, 0.0

    async def analyze_behavioral_signals(
        self,
        user_id: str,
        learning_events: List[LearningEvent] = None,
        clickstream: List[ClickEvent] = None,
        time_on_task_seconds: int = 0
    ) -> BehavioralSignal:
        """
        Analyze all behavioral signals and determine appropriate UI response

        This is the main entry point for behavioral detection.
        """
        if learning_events is None:
            learning_events = []
        if clickstream is None:
            clickstream = []

        # Detect various states
        is_frustrated, frustration_confidence, frustration_reasoning = await self.detect_frustration(
            user_id, learning_events
        )
        is_engaged, engagement_confidence, engagement_reasoning = await self.detect_engagement(
            user_id, clickstream, time_on_task_seconds
        )
        is_struggling, struggling_confidence, struggling_reasoning = await self.detect_struggling(
            user_id, learning_events, time_on_task_seconds
        )
        is_rapid_clicking, rapid_click_confidence = await self.detect_rapid_clicking(
            user_id, clickstream
        )

        # Count consecutive errors
        consecutive_errors = 0
        for event in reversed(learning_events):
            if not event.is_correct:
                consecutive_errors += 1
            else:
                break

        # Determine urgency
        if is_frustrated and consecutive_errors >= self.FRUSTRATION_ERROR_THRESHOLD:
            urgency = UrgencyLevel.INTERVENTION
        elif is_struggling:
            urgency = UrgencyLevel.ATTENTION
        else:
            urgency = UrgencyLevel.NONE

        # Determine suggested mode based on signals
        suggested_mode, mode_reasoning = self._suggest_mode(
            is_frustrated=is_frustrated,
            is_engaged=is_engaged,
            is_struggling=is_struggling,
            is_rapid_clicking=is_rapid_clicking,
            consecutive_errors=consecutive_errors,
            time_on_task_seconds=time_on_task_seconds
        )

        # Calculate overall confidence
        confidence = max(
            frustration_confidence,
            struggling_confidence,
            engagement_confidence
        )

        # Combine reasoning
        all_reasoning = (
            frustration_reasoning +
            engagement_reasoning +
            struggling_reasoning +
            mode_reasoning
        )

        # Calculate last activity
        last_activity_seconds_ago = 0
        if clickstream:
            last_activity_seconds_ago = int(
                (datetime.utcnow() - clickstream[-1].timestamp).total_seconds()
            )

        return BehavioralSignal(
            user_id=user_id,
            is_frustrated=is_frustrated,
            is_engaged=is_engaged,
            is_struggling=is_struggling,
            consecutive_errors=consecutive_errors,
            time_on_task_seconds=time_on_task_seconds,
            last_activity_seconds_ago=last_activity_seconds_ago,
            suggested_mode=suggested_mode,
            urgency=urgency,
            confidence=confidence,
            reasoning=all_reasoning
        )

    def _suggest_mode(
        self,
        is_frustrated: bool,
        is_engaged: bool,
        is_struggling: bool,
        is_rapid_clicking: bool,
        consecutive_errors: int,
        time_on_task_seconds: int
    ) -> tuple[str, List[str]]:
        """
        Suggest appropriate UI mode based on behavioral signals
        """
        reasoning = []

        # Highest priority: Frustration + consecutive errors
        if is_frustrated and consecutive_errors >= self.FRUSTRATION_ERROR_THRESHOLD:
            reasoning.append(f"High frustration + {consecutive_errors} errors")
            return "high_contrast_focus", reasoning

        # Second priority: Struggling
        if is_struggling:
            reasoning.append(f"User struggling (time: {time_on_task_seconds}s)")
            return "focus", reasoning

        # Third priority: Rapid clicking (agitation)
        if is_rapid_clicking:
            reasoning.append("Rapid clicking detected")
            return "focus", reasoning

        # Default: engaged users stay in standard
        if is_engaged:
            reasoning.append("User engaged, maintaining standard mode")
            return "standard", reasoning

        # Fallback
        reasoning.append("Default mode selection")
        return "standard", reasoning


# Singleton instance
behavioral_detector = BehavioralDetector()
