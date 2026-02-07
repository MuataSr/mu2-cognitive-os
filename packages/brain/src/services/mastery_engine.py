"""
MasteryEngine - Bayesian Knowledge Tracing Service
Implements pyBKT for student mastery prediction

This service provides:
- BKT-based mastery probability updates
- Status classification (MASTERED, LEARNING, STRUGGLING)
- Reset protocol for students returning after absence
- FERPA-compliant local-only processing
"""

from typing import Optional, Literal, Dict, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import asyncio


class MasteryState(BaseModel):
    """Student's mastery state for a specific skill"""
    user_id: str
    skill_id: str
    probability_mastery: float  # 0.0 to 1.0
    total_attempts: int = 0
    correct_attempts: int = 0
    consecutive_correct: int = 0
    consecutive_incorrect: int = 0
    last_attempt_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class MasteryStatus(BaseModel):
    """Status classification for UI display"""
    status: Literal["MASTERED", "LEARNING", "STRUGGLING"]
    probability_mastery: float
    attempts: int
    suggested_action: Optional[str] = None
    confidence: float  # How confident we are in this classification


class LearningEvent(BaseModel):
    """A single learning interaction"""
    user_id: str
    skill_id: str
    is_correct: bool
    attempts: int = 1
    time_spent_seconds: Optional[int] = None
    metadata: Dict[str, Any] = {}
    timestamp: datetime = None

    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class MasteryEngine:
    """
    Bayesian Knowledge Tracing implementation

    Simplified BKT formula:
    P(L_t) = P(L_t | L_{t-1}) * P(L_{t-1}) + P(L_t | ~L_{t-1}) * (1 - P(L_{t-1}))

    Where:
    - P(L_t) = probability of knowing the skill at time t
    - P(L_t | L_{t-1}) = 1 - slip (probability of staying in mastery)
    - P(L_t | ~L_{t-1}) = learn_rate (probability of transitioning to mastery)

    Red Dot Logic:
    - STRUGGLING: mastery < 0.6 AND attempts > 3
    - MASTERED: mastery > 0.9
    - LEARNING: everything else
    """

    # Default BKT parameters (can be calibrated with pyBKT)
    DEFAULT_LEARN_RATE = 0.1      # Probability of learning from practice
    DEFAULT_SLIP = 0.05           # Probability of error despite knowing
    DEFAULT_GUESS = 0.2           # Probability of correct without knowing
    DEFAULT_RESET_THRESHOLD_HOURS = 24.0  # Hours before uncertainty increases

    def __init__(
        self,
        learn_rate: float = DEFAULT_LEARN_RATE,
        slip: float = DEFAULT_SLIP,
        guess: float = DEFAULT_GUESS,
        reset_threshold_hours: float = DEFAULT_RESET_THRESHOLD_HOURS
    ):
        """
        Initialize MasteryEngine with BKT parameters

        Args:
            learn_rate: Probability of transitioning to mastery after practice
            slip: Probability of making an error despite knowing the skill
            guess: Probability of answering correctly without knowing
            reset_threshold_hours: Hours away before uncertainty increases
        """
        self.learn_rate = learn_rate
        self.slip = slip
        self.guess = guess
        self.reset_threshold_hours = reset_threshold_hours

    def update_state(
        self,
        is_correct: bool,
        current_mastery: float = 0.5
    ) -> float:
        """
        Update mastery probability using BKT formula

        Args:
            is_correct: Whether the student's answer was correct
            current_mastery: Current mastery probability (default 0.5)

        Returns:
            New mastery probability (0.0 to 1.0)
        """
        # Ensure valid input
        current_mastery = max(0.01, min(0.99, current_mastery))

        if is_correct:
            # Evidence of mastery
            # P(mastery | correct) using Bayes' theorem
            numerator = (1 - self.slip) * current_mastery
            denominator = (1 - self.slip) * current_mastery + self.guess * (1 - current_mastery)
            new_mastery = numerator / denominator if denominator > 0 else current_mastery
        else:
            # Evidence of non-mastery
            # P(mastery | incorrect) using Bayes' theorem
            numerator = self.slip * current_mastery
            denominator = self.slip * current_mastery + (1 - self.guess) * (1 - current_mastery)
            new_mastery = numerator / denominator if denominator > 0 else current_mastery

        # Clamp to valid range (avoid 0 and 1 for computational stability)
        new_mastery = max(0.01, min(0.99, new_mastery))

        return new_mastery

    def get_status(self, state: MasteryState) -> MasteryStatus:
        """
        Determine student status based on mastery probability

        Args:
            state: Current mastery state

        Returns:
            MasteryStatus with classification and suggested action
        """
        mastery = state.probability_mastery
        attempts = state.total_attempts

        # Calculate confidence based on attempt count
        confidence = min(1.0, attempts / 10.0)  # Reaches 100% confidence after 10 attempts

        if mastery < 0.6 and attempts > 3:
            return MasteryStatus(
                status="STRUGGLING",
                probability_mastery=mastery,
                attempts=attempts,
                suggested_action="Provide remediation and scaffolding",
                confidence=confidence
            )
        elif mastery > 0.9:
            return MasteryStatus(
                status="MASTERED",
                probability_mastery=mastery,
                attempts=attempts,
                suggested_action="Ready for next challenge",
                confidence=confidence
            )
        else:
            return MasteryStatus(
                status="LEARNING",
                probability_mastery=mastery,
                attempts=attempts,
                suggested_action="Continue practice",
                confidence=confidence
            )

    def apply_reset_protocol(
        self,
        state: MasteryState,
        hours_since_last: float
    ) -> MasteryState:
        """
        Rapid Re-engagement: Increase uncertainty after time away

        If student has been away longer than reset_threshold_hours,
        increase uncertainty by moving probability toward 0.5

        This addresses the "forgetting curve" - students may have
        partially forgotten mastered skills after extended absence.

        Args:
            state: Current mastery state
            hours_since_last: Hours since last attempt

        Returns:
            Adjusted MasteryState
        """
        if hours_since_last < self.reset_threshold_hours:
            return state

        # Move toward 0.5 (maximum uncertainty)
        # Max 20% adjustment after a week away
        uncertainty_factor = min(
            0.2,
            (hours_since_last - self.reset_threshold_hours) / 168.0
        )

        adjusted_mastery = (
            state.probability_mastery * (1 - uncertainty_factor) +
            0.5 * uncertainty_factor
        )

        state.probability_mastery = adjusted_mastery
        return state

    def process_event(self, event: LearningEvent, current_state: Optional[MasteryState] = None) -> MasteryState:
        """
        Process a learning event and return updated mastery state

        Args:
            event: The learning event to process
            current_state: Current mastery state (if exists)

        Returns:
            Updated MasteryState
        """
        # Get current mastery or initialize
        if current_state:
            current_mastery = current_state.probability_mastery
            total_attempts = current_state.total_attempts + event.attempts
            correct_attempts = current_state.correct_attempts + (1 if event.is_correct else 0)
        else:
            current_mastery = 0.5
            total_attempts = event.attempts
            correct_attempts = 1 if event.is_correct else 0

        # Apply reset protocol if applicable
        if current_state and current_state.last_attempt_at:
            hours_since = (event.timestamp - current_state.last_attempt_at).total_seconds() / 3600
            if hours_since > self.reset_threshold_hours:
                temp_state = MasteryState(
                    user_id=event.user_id,
                    skill_id=event.skill_id,
                    probability_mastery=current_mastery
                )
                temp_state = self.apply_reset_protocol(temp_state, hours_since)
                current_mastery = temp_state.probability_mastery

        # Update mastery using BKT
        new_mastery = self.update_state(event.is_correct, current_mastery)

        # Update consecutive counters
        if event.is_correct:
            consecutive_correct = (current_state.consecutive_correct + 1) if current_state else 1
            consecutive_incorrect = 0
        else:
            consecutive_correct = 0
            consecutive_incorrect = (current_state.consecutive_incorrect + 1) if current_state else 1

        return MasteryState(
            user_id=event.user_id,
            skill_id=event.skill_id,
            probability_mastery=new_mastery,
            total_attempts=total_attempts,
            correct_attempts=correct_attempts,
            consecutive_correct=consecutive_correct,
            consecutive_incorrect=consecutive_incorrect,
            last_attempt_at=event.timestamp
        )

    def predict_next_attempt(self, state: MasteryState) -> float:
        """
        Predict probability of correct answer on next attempt

        Args:
            state: Current mastery state

        Returns:
            Predicted probability of correct answer
        """
        # P(correct) = P(correct | mastery) * P(mastery) + P(correct | ~mastery) * P(~mastery)
        prob_correct = (
            (1 - self.slip) * state.probability_mastery +
            self.guess * (1 - state.probability_mastery)
        )
        return prob_correct

    def needs_intervention(self, state: MasteryState) -> bool:
        """
        Check if student needs teacher intervention

        Args:
            state: Current mastery state

        Returns:
            True if intervention recommended
        """
        return (
            state.probability_mastery < 0.6 and
            state.total_attempts > 3 and
            state.consecutive_incorrect >= 2
        )


# Singleton instance for application-wide use
mastery_engine = MasteryEngine()


def get_mastery_color(status: str) -> str:
    """Get Tailwind color class for mastery status"""
    colors = {
        "MASTERED": "bg-green-500",
        "LEARNING": "bg-yellow-500",
        "STRUGGLING": "bg-red-500"
    }
    return colors.get(status, "bg-gray-500")


def mask_student_id(user_id: str, user_role: str) -> str:
    """
    Mask student ID for non-teacher roles (FERPA compliance)

    Args:
        user_id: Full student identifier
        user_role: Role of the viewer

    Returns:
        Masked or full ID based on role
    """
    if user_role in ["researcher", "external"]:
        return user_id[:8] + "..." if len(user_id) > 8 else "***"
    return user_id
