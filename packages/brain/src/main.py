"""
Mu2 Cognitive OS - Brain Package
FastAPI application with LangGraph state machine
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any, Dict, List
from datetime import datetime
import os
from collections import defaultdict

from src.graph.morning_circle import morning_circle_graph
from src.core.config import settings
from src.services.question_bank import (
    question_bank,
    Question,
    QuestionType,
    DifficultyLevel,
    Subject,
    QuestionBank
)

# In-memory event storage for behavioral tracking
# In production, this would be a Redis or database
_behavioral_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
_click_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

app = FastAPI(
    title="Mu2 Cognitive OS - Brain API",
    description="Backend service implementing LangGraph state machines and LlamaIndex retrieval",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration - allow local development only (NO CLOUD)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatInput(BaseModel):
    """Input for the morning circle state machine"""

    message: str = Field(..., description="User's input message")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    session_id: Optional[str] = Field(None, description="Optional session identifier")
    mode: Literal["standard", "focus"] = Field("standard", description="Current UI mode")


class SentimentResult(BaseModel):
    """Sentiment analysis result"""

    score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score from -1 (negative) to 1 (positive)")
    label: Literal["positive", "neutral", "negative"] = Field(..., description="Sentiment label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class ChatOutput(BaseModel):
    """Output from the morning circle state machine"""

    response: str = Field(..., description="Generated response")
    sentiment: SentimentResult = Field(..., description="Sentiment analysis of input")
    suggested_mode: Literal["standard", "focus"] = Field(..., description="Suggested UI mode based on context")
    retrieval_type: Literal["fact", "concept"] = Field(..., description="Type of retrieval performed")
    sources: list[str] = Field(default_factory=list, description="List of sources used")

    # Hybrid LLM Metadata
    llm_provider_used: Optional[str] = Field(None, description="LLM provider used (local/cloud)")
    llm_routing_reason: Optional[str] = Field(None, description="Reason for provider selection")
    complexity_score: Optional[float] = Field(None, description="Query complexity score")

    # Anonymization Metadata (FERPA Compliance)
    was_anonymized: bool = Field(default=False, description="Whether input was anonymized")
    pii_detected: bool = Field(default=False, description="Whether PII was detected in input")
    anonymization_summary: Optional[dict[str, Any]] = Field(None, description="Summary of anonymization (no original text)")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    version: str
    database: str


# Endpoints
@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {"message": "Mu2 Cognitive OS - Brain API", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    # TODO: Add actual database connectivity check
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        database="connected",
    )


@app.get("/api/v1/status", tags=["Status"])
async def status() -> dict[str, str]:
    """Service status endpoint"""
    return {
        "service": "mu2-brain",
        "status": "operational",
        "graph": "morning_circle",
    }


@app.post("/api/v1/chat", response_model=ChatOutput, tags=["Chat"])
async def chat(input_data: ChatInput) -> ChatOutput:
    """
    Main chat endpoint using the Morning Circle state machine

    Flow: Input -> Anonymization -> Sentiment Analysis -> Context Routing -> Retrieval -> Output

    FERPA Compliance:
    - All input is anonymized before processing
    - PII is detected and removed
    - Original text never logged or sent to external services
    """
    try:
        # Run the morning circle graph
        result = await morning_circle_graph.ainvoke(
            {
                "message": input_data.message,
                "mode": input_data.mode,
                "user_id": input_data.user_id,
                "sources": [],
                "retrieved_context": {}
            }
        )

        # Extract anonymization metadata
        anonymization_metadata = result.get("anonymization_metadata", {})
        was_anonymized = anonymization_metadata is not None
        pii_detected = anonymization_metadata.get("pii_count", 0) > 0 if anonymization_metadata else False

        # Build output
        output = ChatOutput(
            response=result.get("response", ""),
            sentiment=SentimentResult(
                score=result.get("sentiment_score", 0.0),
                label=result.get("sentiment_label", "neutral"),
                confidence=0.8  # Placeholder
            ),
            suggested_mode=result.get("mode", "standard"),
            retrieval_type=result.get("retrieval_type", "fact"),
            sources=result.get("sources", []),
            llm_provider_used=result.get("llm_provider_used"),
            llm_routing_reason=result.get("llm_routing_reason"),
            complexity_score=result.get("complexity_score"),
            was_anonymized=was_anonymized,
            pii_detected=pii_detected,
            anonymization_summary={
                "method": anonymization_metadata.get("anonymization_method"),
                "pii_count": anonymization_metadata.get("pii_count", 0),
                "entities_detected": anonymization_metadata.get("entities_detected", [])
            } if anonymization_metadata else None
        )

        return output

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/api/v1/modes", tags=["Modes"])
async def get_modes() -> dict[str, list[str]]:
    """Get available UI modes"""
    return {"modes": ["standard", "focus"]}


@app.post("/api/v1/modes/suggest", tags=["Modes"])
async def suggest_mode(input_data: ChatInput) -> dict[str, str]:
    """
    Suggest appropriate mode based on input

    This is a simplified version - the full version would use
    more sophisticated analysis of the input content.
    """
    # Simple heuristic: longer, complex inputs benefit from focus mode
    word_count = len(input_data.message.split())
    suggested = "focus" if word_count > 50 else "standard"

    return {"suggested_mode": suggested, "reason": f"Word count: {word_count}"}


@app.post("/api/v1/vectorstore/health", tags=["Vector Store"])
async def vector_store_health() -> dict[str, Any]:
    """Check vector store health"""
    from src.services.sqlite_vector_store import sqlite_vector_store

    health = await sqlite_vector_store.health_check()
    return health


@app.post("/api/v1/vectorstore/populate", tags=["Vector Store"])
async def populate_test_data() -> dict[str, str]:
    """Populate vector store with test data"""
    # Note: This endpoint is deprecated for the simple vector store
    # Use direct SQL inserts or seed_data.sql instead
    return {"status": "error", "message": "This endpoint is deprecated. Use seed_data.sql for populating data."}


# ============================================================================
# Mastery Tracking API Endpoints
# Bayesian Knowledge Tracing for student mastery tracking
# ============================================================================

# Mastery Tracking Request/Response Models
class LearningEventInput(BaseModel):
    """Input for recording a learning event"""
    user_id: str = Field(..., description="Student user ID")
    skill_id: str = Field(..., description="Skill being practiced")
    is_correct: bool = Field(..., description="Whether the answer was correct")
    attempts: int = Field(1, ge=1, description="Number of attempts for this question")
    time_spent_seconds: Optional[int] = Field(None, ge=0, description="Time spent on this question")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")


class MasteryStatusOutput(BaseModel):
    """Mastery status classification"""
    status: Literal["MASTERED", "LEARNING", "STRUGGLING"]
    probability_mastery: float
    attempts: int
    suggested_action: Optional[str]
    confidence: float


class MasteryUpdateOutput(BaseModel):
    """Output after recording a learning event"""
    user_id: str
    skill_id: str
    previous_mastery: float
    new_mastery: float
    status: MasteryStatusOutput
    predicted_next: float


class StudentSkillOutput(BaseModel):
    """Single skill mastery state"""
    skill_id: str
    skill_name: str
    probability_mastery: float
    total_attempts: int
    correct_attempts: int
    status: MasteryStatusOutput


class LiveFeedEvent(BaseModel):
    """Event for Live Feed sidebar"""
    user_id: str
    event_type: Literal["STUDENT_ACTION", "AGENT_ACTION"]
    timestamp: str
    source_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecentEventsOutput(BaseModel):
    """Recent learning events for Live Feed"""
    events: list[LiveFeedEvent]
    count: int


class StudentSkillsOutput(BaseModel):
    """All mastery states for a student"""
    user_id: str
    skills: list[StudentSkillOutput]
    total_skills: int
    mastered_count: int
    learning_count: int
    struggling_count: int
    recent_events: list[LiveFeedEvent] = Field(default_factory=list, description="Recent learning events with source text")


class StudentCardOutput(BaseModel):
    """Summary card for teacher dashboard"""
    user_id: str
    masked_id: str
    total_skills: int
    mastered_count: int
    learning_count: int
    struggling_count: int
    avg_mastery: float
    overall_status: Literal["MASTERED", "LEARNING", "STRUGGLING"]
    last_active: str


class ClassOverviewOutput(BaseModel):
    """Class-wide mastery overview for teachers"""
    students: list[StudentCardOutput]
    total_students: int
    struggling_students: int
    class_avg_mastery: float
    count_ready: int = Field(default=0, description="Number of students with MASTERED status")
    count_distracted: int = Field(default=0, description="Number of students with LEARNING status")
    count_intervention: int = Field(default=0, description="Number of students with STRUGGLING status")


@app.post("/api/v1/mastery/record", response_model=MasteryUpdateOutput, tags=["Mastery"])
async def record_learning_event(event: LearningEventInput) -> MasteryUpdateOutput:
    """
    Record a learning event and update mastery probability using BKT

    This endpoint:
    1. Records the learning interaction in the database
    2. Updates mastery probability using Bayesian Knowledge Tracing
    3. Returns the new mastery state with classification

    Example:
    ```json
    {
      "user_id": "student-123",
      "skill_id": "photosynthesis-basics",
      "is_correct": true,
      "attempts": 1,
      "time_spent_seconds": 45
    }
    ```
    """
    from src.services.mastery_engine import mastery_engine, MasteryState, LearningEvent as MasteryLearningEvent

    try:
        # In a full implementation, we would:
        # 1. Connect to database to get current state
        # 2. Process the event through MasteryEngine
        # 3. Save the new state to database
        # For now, we'll do a simplified in-memory version

        # Simulate getting current state (would come from DB)
        current_mastery = 0.5  # Default for new skills

        # Process the event
        new_mastery = mastery_engine.update_state(
            is_correct=event.is_correct,
            current_mastery=current_mastery
        )

        # Create a temporary state for status classification
        temp_state = MasteryState(
            user_id=event.user_id,
            skill_id=event.skill_id,
            probability_mastery=new_mastery,
            total_attempts=1,
            correct_attempts=1 if event.is_correct else 0
        )

        status = mastery_engine.get_status(temp_state)
        predicted_next = mastery_engine.predict_next_attempt(temp_state)

        return MasteryUpdateOutput(
            user_id=event.user_id,
            skill_id=event.skill_id,
            previous_mastery=current_mastery,
            new_mastery=new_mastery,
            status=status,
            predicted_next=predicted_next
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording learning event: {str(e)}")


@app.get("/api/v1/mastery/student/{user_id}", response_model=StudentSkillsOutput, tags=["Mastery"])
async def get_student_mastery(user_id: str) -> StudentSkillsOutput:
    """
    Get all mastery states for a specific student

    Returns:
        - All skills the student has practiced
        - Mastery probability for each skill
        - Status classification (MASTERED/LEARNING/STRUGGLING)
        - Summary statistics

    Example:
    ```json
    {
      "user_id": "student-123",
      "skills": [
        {
          "skill_id": "photosynthesis-basics",
          "skill_name": "Photosynthesis Basics",
          "probability_mastery": 0.85,
          "total_attempts": 8,
          "correct_attempts": 7,
          "status": {
            "status": "LEARNING",
            "suggested_action": "Continue practice"
          }
        }
      ],
      "total_skills": 5,
      "mastered_count": 2,
      "learning_count": 2,
      "struggling_count": 1
    }
    ```
    """
    from src.services.mastery_engine import mastery_engine, MasteryState

    try:
        # In a full implementation, query from database
        # For now, return sample data
        sample_skills = [
            {
                "skill_id": "photosynthesis-basics",
                "skill_name": "Photosynthesis Basics",
                "probability_mastery": 0.85,
                "total_attempts": 8,
                "correct_attempts": 7
            },
            {
                "skill_id": "light-reactions",
                "skill_name": "Light-Dependent Reactions",
                "probability_mastery": 0.45,
                "total_attempts": 5,
                "correct_attempts": 2
            },
            {
                "skill_id": "calvin-cycle",
                "skill_name": "Calvin Cycle",
                "probability_mastery": 0.92,
                "total_attempts": 12,
                "correct_attempts": 11
            }
        ]

        skills_output = []
        mastered_count = 0
        learning_count = 0
        struggling_count = 0

        for skill_data in sample_skills:
            state = MasteryState(
                user_id=user_id,
                skill_id=skill_data["skill_id"],
                probability_mastery=skill_data["probability_mastery"],
                total_attempts=skill_data["total_attempts"],
                correct_attempts=skill_data["correct_attempts"]
            )
            status = mastery_engine.get_status(state)

            if status.status == "MASTERED":
                mastered_count += 1
            elif status.status == "STRUGGLING":
                struggling_count += 1
            else:
                learning_count += 1

            skills_output.append(
                StudentSkillOutput(
                    skill_id=skill_data["skill_id"],
                    skill_name=skill_data["skill_name"],
                    probability_mastery=skill_data["probability_mastery"],
                    total_attempts=skill_data["total_attempts"],
                    correct_attempts=skill_data["correct_attempts"],
                    status=status.model_dump()
                )
            )

        # Generate recent events for this student
        from datetime import timedelta
        recent_events = []
        actions = [
            "Movement break completed",
            "Question answered correctly",
            "Hint provided",
            "Focus mode activated",
            "Review suggested",
        ]

        for i in range(5):
            event_time = datetime.utcnow() - timedelta(hours=i * 2)
            is_agent = i % 2 == 0
            recent_events.append(
                LiveFeedEvent(
                    user_id=user_id,
                    event_type="AGENT_ACTION" if is_agent else "STUDENT_ACTION",
                    timestamp=event_time.isoformat(),
                    source_text=actions[i % len(actions)] if is_agent else None,
                    metadata={"skill_id": sample_skills[i % len(sample_skills)]["skill_id"]}
                )
            )

        return StudentSkillsOutput(
            user_id=user_id,
            skills=skills_output,
            total_skills=len(skills_output),
            mastered_count=mastered_count,
            learning_count=learning_count,
            struggling_count=struggling_count,
            recent_events=recent_events
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving student mastery: {str(e)}")


@app.get("/api/v1/mastery/class", response_model=ClassOverviewOutput, tags=["Mastery"])
async def get_class_mastery(
    struggling_only: bool = False,
    min_mastery: float = 0.0
) -> ClassOverviewOutput:
    """
    Get mastery overview for all students (Teacher Dashboard)

    This is the "Air Traffic Control" view for teachers:
    - See all students at a glance
    - Red/Yellow/Green status indicators
    - Filter by struggling students
    - Real-time updates

    Query Parameters:
    - struggling_only: If true, only return students who are struggling
    - min_mastery: Filter students by minimum average mastery

    Example:
    ```json
    {
      "students": [
        {
          "user_id": "student-123",
          "masked_id": "student-...",
          "total_skills": 5,
          "mastered_count": 2,
          "learning_count": 2,
          "struggling_count": 1,
          "avg_mastery": 0.74,
          "overall_status": "LEARNING",
          "last_active": "2025-01-15T10:30:00Z"
        }
      ],
      "total_students": 25,
      "struggling_students": 3,
      "class_avg_mastery": 0.68
    }
    ```
    """
    from src.services.mastery_engine import mastery_engine, MasteryState, mask_student_id

    try:
        # In a full implementation, query from database
        # For now, return sample data
        sample_students = [
            {
                "user_id": "student-001",
                "total_skills": 5,
                "mastered_count": 2,
                "learning_count": 2,
                "struggling_count": 1,
                "avg_mastery": 0.74,
                "last_active": datetime.utcnow().isoformat()
            },
            {
                "user_id": "student-002",
                "total_skills": 5,
                "mastered_count": 4,
                "learning_count": 1,
                "struggling_count": 0,
                "avg_mastery": 0.92,
                "last_active": datetime.utcnow().isoformat()
            },
            {
                "user_id": "student-003",
                "total_skills": 5,
                "mastered_count": 0,
                "learning_count": 2,
                "struggling_count": 3,
                "avg_mastery": 0.42,
                "last_active": datetime.utcnow().isoformat()
            }
        ]

        students_output = []
        struggling_count = 0
        total_mastery = 0

        for student_data in sample_students:
            # Apply filters
            if struggling_only and student_data["struggling_count"] == 0:
                continue
            if student_data["avg_mastery"] < min_mastery:
                continue

            # Determine overall status
            if student_data["struggling_count"] > 0:
                overall_status = "STRUGGLING"
                struggling_count += 1
            elif student_data["avg_mastery"] > 0.85:
                overall_status = "MASTERED"
            else:
                overall_status = "LEARNING"

            total_mastery += student_data["avg_mastery"]

            students_output.append(
                StudentCardOutput(
                    user_id=student_data["user_id"],
                    masked_id=mask_student_id(student_data["user_id"], "teacher"),
                    total_skills=student_data["total_skills"],
                    mastered_count=student_data["mastered_count"],
                    learning_count=student_data["learning_count"],
                    struggling_count=student_data["struggling_count"],
                    avg_mastery=student_data["avg_mastery"],
                    overall_status=overall_status,
                    last_active=student_data["last_active"]
                )
            )

        class_avg = total_mastery / len(students_output) if students_output else 0.0

        return ClassOverviewOutput(
            students=students_output,
            total_students=len(students_output),
            struggling_students=struggling_count,
            class_avg_mastery=round(class_avg, 3),
            count_ready=sum(1 for s in students_output if s.overall_status == "MASTERED"),
            count_distracted=sum(1 for s in students_output if s.overall_status == "LEARNING"),
            count_intervention=sum(1 for s in students_output if s.overall_status == "STRUGGLING")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving class mastery: {str(e)}")


@app.get("/api/v1/mastery/recent-events", response_model=RecentEventsOutput, tags=["Mastery"])
async def get_recent_events(limit: int = 20) -> RecentEventsOutput:
    """
    Get recent learning events for the Live Feed sidebar

    This endpoint returns the most recent learning events across all students,
    suitable for displaying in a real-time activity feed.

    Query Parameters:
    - limit: Maximum number of events to return (default: 20)

    Example:
    ```json
    {
      "events": [
        {
          "user_id": "student-001",
          "event_type": "AGENT_ACTION",
          "timestamp": "2025-01-15T10:30:00Z",
          "source_text": "Movement break completed",
          "metadata": {"action_type": "break"}
        }
      ],
      "count": 20
    }
    ```
    """
    try:
        # In a full implementation, query from database
        # For now, return sample data with realistic timestamps
        from datetime import timedelta

        sample_events = []
        actions = [
            "Movement break completed",
            "Question answered correctly",
            "Hint provided",
            "Skill mastered",
            "Focus mode activated",
            "Review suggested",
            "Practice started",
        ]

        for i in range(min(limit, 20)):
            event_time = datetime.utcnow() - timedelta(minutes=i * 2)
            is_agent = i % 3 == 0  # Every third event is an agent action

            sample_events.append(
                LiveFeedEvent(
                    user_id=f"student-{(i % 3) + 1:03d}",
                    event_type="AGENT_ACTION" if is_agent else "STUDENT_ACTION",
                    timestamp=event_time.isoformat(),
                    source_text=actions[i % len(actions)] if is_agent else None,
                    metadata={"index": i}
                )
            )

        return RecentEventsOutput(
            events=sample_events,
            count=len(sample_events)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving recent events: {str(e)}")


@app.get("/api/v1/mastery/skills", tags=["Mastery"])
async def list_available_skills(
    subject: Optional[str] = None,
    grade_level: Optional[int] = None
) -> Dict[str, Any]:
    """
    List all available skills in the registry

    Query Parameters:
    - subject: Filter by subject (e.g., "biology", "chemistry")
    - grade_level: Filter by grade level

    Returns:
        List of skills with metadata
    """
    try:
        # In a full implementation, query from database
        # For now, return sample data
        sample_skills = [
            {
                "skill_id": "photosynthesis-basics",
                "skill_name": "Photosynthesis Basics",
                "subject": "biology",
                "grade_level": 8,
                "description": "Understanding the fundamental process of photosynthesis"
            },
            {
                "skill_id": "light-reactions",
                "skill_name": "Light-Dependent Reactions",
                "subject": "biology",
                "grade_level": 9,
                "description": "Understanding ATP and NADPH production in photosynthesis"
            },
            {
                "skill_id": "calvin-cycle",
                "skill_name": "Calvin Cycle",
                "subject": "biology",
                "grade_level": 9,
                "description": "Understanding carbon fixation and glucose production"
            },
            {
                "skill_id": "cellular-respiration",
                "skill_name": "Cellular Respiration",
                "subject": "biology",
                "grade_level": 9,
                "description": "Understanding how cells convert glucose to energy"
            }
        ]

        # Apply filters
        filtered_skills = sample_skills
        if subject:
            filtered_skills = [s for s in filtered_skills if s["subject"] == subject]
        if grade_level:
            filtered_skills = [s for s in filtered_skills if s["grade_level"] == grade_level]

        return {
            "skills": filtered_skills,
            "count": len(filtered_skills),
            "filters": {"subject": subject, "grade_level": grade_level}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing skills: {str(e)}")


@app.get("/api/v1/vectorstore/query", tags=["Vector Store"])
async def query_vector_store(q: str, retrieval_type: str = "fact", top_k: int = 5) -> dict[str, Any]:
    """
    Query the vector store directly

    Args:
        q: Search query
        retrieval_type: Type of retrieval ('fact' or 'concept')
        top_k: Number of results to return
    """
    from src.services.sqlite_vector_store import sqlite_vector_store

    if retrieval_type == "fact":
        results = await sqlite_vector_store.retrieve_facts(q, top_k=top_k)
    elif retrieval_type == "concept":
        results = await sqlite_vector_store.retrieve_concepts(q, top_k=top_k)
    else:
        results = await sqlite_vector_store.retrieve_hybrid(q, top_k=top_k)

    return {"query": q, "retrieval_type": retrieval_type, "results": results, "count": len(results)}


# ============================================================================
# Behavioral Detection API Endpoints
# ============================================================================

class ClickEventInput(BaseModel):
    """Input for clickstream event tracking"""
    user_id: str = Field(..., description="Student user ID")
    x: int = Field(..., ge=0, description="X coordinate (relative to viewport)")
    y: int = Field(..., ge=0, description="Y coordinate (relative to viewport)")
    element_id: Optional[str] = Field(None, description="ID of clicked element")
    element_type: Optional[str] = Field(None, description="Type of element (button, link, text)")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp (defaults to now)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event data")

class BehavioralEventInput(BaseModel):
    """Input for behavioral event tracking"""
    user_id: str = Field(..., description="Student user ID")
    event_type: Literal["squinting", "frustration", "engagement", "abandonment", "rapid_clicking", "long_pause"] = Field(
        ..., description="Type of behavioral event"
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event data")


class BehavioralStatusOutput(BaseModel):
    """Output from behavioral analysis"""
    user_id: str
    is_frustrated: bool
    is_engaged: bool
    is_struggling: bool
    consecutive_errors: int
    time_on_task_seconds: int
    suggested_mode: Literal["standard", "focus", "high_contrast_focus", "exploration"]
    urgency: Literal["none", "attention", "intervention"]
    confidence: float
    reasoning: list[str]


class LearningEventsBatch(BaseModel):
    """Batch of learning events for behavioral analysis"""
    user_id: str = Field(..., description="Student user ID")
    events: list[Dict[str, Any]] = Field(..., description="Learning events (is_correct, attempts, time_spent)")
    time_on_task_seconds: int = Field(60, ge=0, description="Total time on current task")


@app.post("/api/v1/behavioral/analyze", response_model=BehavioralStatusOutput, tags=["Behavioral"])
async def analyze_behavioral_status(input_data: LearningEventsBatch) -> BehavioralStatusOutput:
    """
    Analyze behavioral signals and determine appropriate UI mode

    This endpoint:
    1. Processes recent learning events
    2. Detects frustration, engagement, struggle
    3. Suggests appropriate UI mode
    4. Determines intervention urgency

    Example:
    ```json
    {
      "user_id": "student-123",
      "events": [
        {"skill_id": "photosynthesis", "is_correct": false, "attempts": 3, "time_spent_seconds": 180},
        {"skill_id": "photosynthesis", "is_correct": false, "attempts": 2, "time_spent_seconds": 120}
      ],
      "time_on_task_seconds": 300
    }
    ```
    """
    from src.services.behavioral_detector import behavioral_detector, LearningEvent

    try:
        # Convert input events to LearningEvent objects
        learning_events = []
        for event_data in input_data.events:
            learning_events.append(LearningEvent(
                user_id=input_data.user_id,
                skill_id=event_data.get("skill_id", "unknown"),
                is_correct=event_data.get("is_correct", True),
                attempts=event_data.get("attempts", 1),
                time_spent_seconds=event_data.get("time_spent_seconds", 0)
            ))

        # Analyze behavioral signals
        signals = await behavioral_detector.analyze_behavioral_signals(
            user_id=input_data.user_id,
            learning_events=learning_events,
            clickstream=[],
            time_on_task_seconds=input_data.time_on_task_seconds
        )

        return BehavioralStatusOutput(
            user_id=signals.user_id,
            is_frustrated=signals.is_frustrated,
            is_engaged=signals.is_engaged,
            is_struggling=signals.is_struggling,
            consecutive_errors=signals.consecutive_errors,
            time_on_task_seconds=signals.time_on_task_seconds,
            suggested_mode=signals.suggested_mode,
            urgency=signals.urgency,
            confidence=signals.confidence,
            reasoning=signals.reasoning
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Behavioral analysis error: {str(e)}")


@app.get("/api/v1/behavioral/status/{user_id}", response_model=BehavioralStatusOutput, tags=["Behavioral"])
async def get_behavioral_status(user_id: str) -> BehavioralStatusOutput:
    """
    Get current behavioral status for a student

    Returns the detected behavioral state and suggested UI mode.
    In a full implementation, this would query from a database of recent events.

    Example:
    ```json
    {
      "user_id": "student-123",
      "is_frustrated": true,
      "is_struggling": true,
      "consecutive_errors": 3,
      "suggested_mode": "high_contrast_focus",
      "urgency": "intervention"
    }
    ```
    """
    from src.services.behavioral_detector import behavioral_detector

    try:
        # Get in-memory events for this user
        user_behavioral_events = _behavioral_events.get(user_id, [])
        user_click_events = _click_events.get(user_id, [])

        # Convert to detector format
        learning_events = []
        for event in user_behavioral_events[-20:]:  # Last 20 events
            if "is_correct" in event:
                learning_events.append({
                    "skill_id": "current",
                    "is_correct": event.get("is_correct", True),
                    "attempts": event.get("attempts", 1),
                    "time_spent_seconds": event.get("time_spent_seconds", 0)
                })

        # Convert click events to ClickEvent format
        clickstream = []
        for event in user_click_events[-50:]:  # Last 50 clicks
            clickstream.append({
                "x": event.get("x", 0),
                "y": event.get("y", 0),
                "element_id": event.get("element_id"),
                "timestamp": datetime.fromisoformat(event.get("timestamp", datetime.utcnow().isoformat()))
            })

        # Calculate time on task from most recent event
        time_on_task_seconds = 60  # Default
        if user_behavioral_events:
            last_event = user_behavioral_events[-1]
            if "timestamp" in last_event:
                last_time = datetime.fromisoformat(last_event["timestamp"])
                time_on_task_seconds = int((datetime.utcnow() - last_time).total_seconds())

        signals = await behavioral_detector.analyze_behavioral_signals(
            user_id=user_id,
            learning_events=learning_events,
            clickstream=clickstream,
            time_on_task_seconds=time_on_task_seconds
        )

        return BehavioralStatusOutput(
            user_id=signals.user_id,
            is_frustrated=signals.is_frustrated,
            is_engaged=signals.is_engaged,
            is_struggling=signals.is_struggling,
            consecutive_errors=signals.consecutive_errors,
            time_on_task_seconds=signals.time_on_task_seconds,
            suggested_mode=signals.suggested_mode,
            urgency=signals.urgency,
            confidence=signals.confidence,
            reasoning=signals.reasoning
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving behavioral status: {str(e)}")


@app.post("/api/v1/behavioral/track-event", tags=["Behavioral"])
async def track_behavioral_event(event: BehavioralEventInput) -> Dict[str, str]:
    """
    Track a behavioral event (clickstream, squinting, etc.)

    This endpoint receives behavioral signals from the frontend
    and stores them for analysis.

    In a full implementation, this would store events in a database
    for real-time behavioral analysis.

    Example:
    ```json
    {
      "user_id": "student-123",
      "event_type": "rapid_clicking",
      "confidence": 0.8,
      "metadata": {"click_count": 7, "time_span_seconds": 1.5}
    }
    ```
    """
    try:
        # In a full implementation, store in database
        # For now, just acknowledge
        return {
            "status": "recorded",
            "user_id": event.user_id,
            "event_type": event.event_type,
            "message": "Event recorded successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking event: {str(e)}")


@app.post("/api/v1/behavioral/clickstream", response_model=Dict[str, Any], tags=["Behavioral"])
async def track_clickstream(batch: list[ClickEventInput]) -> Dict[str, Any]:
    """
    Track a batch of click/cursor events for behavioral analysis

    This endpoint receives clickstream data from frontend
    and stores it for frustration/engagement detection.

    Example:
    ```json
    [
      {
        "user_id": "student-123",
        "x": 250,
        "y": 100,
        "element_id": "submit-button",
        "element_type": "button",
        "timestamp": "2025-02-09T10:30:00Z"
      }
    ]
    ```
    """
    try:
        # Store all click events
        stored_count = 0
        for click_event in batch:
            # Use provided timestamp or default to now
            event_ts = click_event.timestamp or datetime.utcnow()

            event_data = {
                "x": click_event.x,
                "y": click_event.y,
                "element_id": click_event.element_id,
                "element_type": click_event.element_type,
                "timestamp": event_ts.isoformat()
            }

            # Get first user_id from batch
            user_id = click_event.user_id
            _click_events[user_id].append(event_data)
            stored_count += 1

        return {
            "status": "success",
            "user_id": user_id,
            "events_stored": stored_count,
            "total_click_events": len(_click_events[user_id])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking clickstream: {str(e)}")


@app.get("/api/v1/vectorstore/query", tags=["Vector Store"])
async def query_vector_store(q: str, retrieval_type: str = "fact", top_k: int = 5) -> dict[str, Any]:
    """
    Query the vector store directly

    Args:
        q: Search query
        retrieval_type: Type of retrieval ('fact' or 'concept')
        top_k: Number of results to return
    """
    from src.services.sqlite_vector_store import sqlite_vector_store

    if retrieval_type == "fact":
        results = await sqlite_vector_store.retrieve_facts(q, top_k=top_k)
    elif retrieval_type == "concept":
        results = await sqlite_vector_store.retrieve_concepts(q, top_k=top_k)
    else:
        results = await sqlite_vector_store.retrieve_hybrid(q, top_k=top_k)

    return {"query": q, "retrieval_type": retrieval_type, "results": results, "count": len(results)}


# ============================================================================
# Hybrid LLM & Anonymization API Endpoints
# ============================================================================

class AnonymizeInput(BaseModel):
    """Input for anonymization test"""
    text: str = Field(..., description="Text to anonymize")
    user_id: Optional[str] = Field(None, description="Optional user ID to mask")


class AnonymizeOutput(BaseModel):
    """Output from anonymization"""
    original_text: str = Field(..., description="Original input text")
    anonymized_text: str = Field(..., description="Text with PII removed")
    has_pii: bool = Field(..., description="Whether PII was detected")
    pii_count: int = Field(..., description="Number of PII entities detected")
    entities_detected: list[dict[str, Any]] = Field(default_factory=list, description="List of detected PII entities")
    safe_for_cloud: bool = Field(..., description="Whether text is safe to send to cloud")


@app.post("/api/v1/test/anonymize", response_model=AnonymizeOutput, tags=["Testing"])
async def test_anonymize(input_data: AnonymizeInput) -> AnonymizeOutput:
    """
    Test the PII anonymization service

    This endpoint demonstrates how the system detects and removes PII
    before sending data to external services.

    Example:
    ```json
    {
      "text": "My name is John Smith and my email is john@example.com",
      "user_id": "student-123"
    }
    ```

    Returns:
        Anonymized text with PII removed
    """
    from src.services.anonymization_service import anonymization_service

    try:
        result = await anonymization_service.anonymize_text(
            text=input_data.text,
            user_id=input_data.user_id,
            include_metadata=True
        )

        return AnonymizeOutput(
            original_text=input_data.text,  # Only for testing - never logged in production
            anonymized_text=result.anonymized_text,
            has_pii=result.has_pii,
            pii_count=result.pii_count,
            entities_detected=result.metadata.get("entities_detected", []),
            safe_for_cloud=result.safe_for_cloud
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anonymization error: {str(e)}")


@app.get("/api/v1/hybrid/health", tags=["Hybrid LLM"])
async def hybrid_health() -> dict[str, Any]:
    """
    Check the health of the hybrid LLM system

    Returns status for:
    - Local Ollama availability
    - Cloud provider configuration
    - Anonymization service status
    """
    from src.services.hybrid_llm_router import hybrid_router

    try:
        health = await hybrid_router.health_check()
        return health
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


class HybridGenerateInput(BaseModel):
    """Input for hybrid LLM generation test"""
    prompt: str = Field(..., description="Prompt to generate from")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(500, ge=1, le=4096)


class HybridGenerateOutput(BaseModel):
    """Output from hybrid LLM generation"""
    response: str = Field(..., description="Generated response")
    provider_used: str = Field(..., description="Which provider was used (local/cloud)")
    routing_reason: str = Field(..., description="Why this provider was chosen")
    complexity_score: float = Field(..., description="Query complexity score")
    was_anonymized: bool = Field(..., description="Whether input was anonymized")
    tokens_used: Optional[int] = Field(None, description="Tokens used for generation")


@app.post("/api/v1/hybrid/generate", response_model=HybridGenerateOutput, tags=["Hybrid LLM"])
async def test_hybrid_generate(input_data: HybridGenerateInput) -> HybridGenerateOutput:
    """
    Test the hybrid LLM router

    This endpoint demonstrates how the system routes between local and cloud LLMs
    based on query complexity, PII detection, and configuration.

    Example:
    ```json
    {
      "prompt": "Explain photosynthesis in detail",
      "user_id": "student-123"
    }
    ```
    """
    from src.services.hybrid_llm_router import hybrid_router, LLMPurpose

    try:
        response = await hybrid_router.generate(
            query=input_data.prompt,
            purpose=LLMPurpose.GENERATION,
            user_id=input_data.user_id,
            temperature=input_data.temperature,
            max_tokens=input_data.max_tokens
        )

        routing = response.raw_response.get("routing_decision", {}) if response.raw_response else {}

        return HybridGenerateOutput(
            response=response.text,
            provider_used=routing.get("provider", "unknown"),
            routing_reason=routing.get("reason", ""),
            complexity_score=routing.get("complexity_score", 0.0),
            was_anonymized=routing.get("was_anonymized", False),
            tokens_used=response.tokens_used
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hybrid generation error: {str(e)}")


# ============================================================================
# V2 API - Router Engine Endpoints
# TEMPORARILY DISABLED: These endpoints import router_engine and graph_store_service
# which depend on Postgres (psycopg2). Commented out to use SQLite-only stack.
# ============================================================================

# class QueryInput(BaseModel):
#     """Input for the router query"""
#
#     query: str = Field(..., description="User's query")
#     retrieve_mode: Optional[Literal["auto", "vector", "graph"]] = Field(
#         "auto", description="Retrieval mode (auto, vector, or graph)"
#     )
#
#
# class TranslationInput(BaseModel):
#     """Input for grade-level translation"""
#
#     text: str = Field(..., description="College-level text to translate")
#     grade_level: int = Field(..., ge=1, le=12, description="Target grade level (1-12)")
#     source_id: Optional[str] = Field(None, description="Source ID for citation")
#
#
# class QueryOutput(BaseModel):
#     """Output from router query"""
#
#     query: str = Field(..., description="Original query")
#     result: str = Field(..., description="Query result")
#     engine_used: str = Field(..., description="Which engine handled the query")
#     query_type: Literal["fact", "concept"] = Field(..., description="Query classification")
#
#
# class TranslationOutput(BaseModel):
#     """Output from translation"""
#
#     simplified: str = Field(..., description="Simplified explanation")
#     metaphor: str = Field(..., description="Real-world metaphor")
#     source_id: str = Field(..., description="Source ID for citation")
#     confidence: float = Field(..., description="Confidence score (0-1)")
#     key_terms: list[str] = Field(default_factory=list, description="Key terms to remember")
#
#
# @app.post("/api/v2/query", response_model=QueryOutput, tags=["Router"])
# async def router_query(input_data: QueryInput) -> QueryOutput:
#     """
#     Main query endpoint using the Router Engine
#
#     The router automatically determines whether to use:
#     - Vector Store (facts): "What is X?", "Define X", "List X"
#     - Graph Store (concepts): "How does X relate to Y?", "Why X?", "Compare X and Y"
#
#     Example queries:
#     - Vector: "What is photosynthesis?"
#     - Graph: "How does sunlight affect photosynthesis?"
#     """
#     from src.services.router_engine import router_engine
#
#     try:
#         result = await router_engine.query(
#             query_str=input_data.query,
#             retrieve_mode=input_data.retrieve_mode,
#         )
#
#         return QueryOutput(**result)
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Query processing error: {str(e)}")
#
#
# @app.post("/api/v2/translate", response_model=TranslationOutput, tags=["Router"])
# async def translate_text(input_data: TranslationInput) -> TranslationOutput:
#     """
#     Translate college-level text to appropriate grade level
#
#     This endpoint uses "The Translator" prompt to:
#     1. Simplify complex explanations
#     2. Provide real-world metaphors
#     3. Include source citations
#
#     Example:
#     - Input: "Photosynthesis is the process by which plants convert light energy into chemical energy..."
#     - Output: Simplified explanation + metaphor for 6th graders
#     """
#     from src.services.router_engine import router_engine
#
#     try:
#         result = await router_engine.translate_to_grade_level(
#             college_text=input_data.text,
#             grade_level=input_data.grade_level,
#             source_id=input_data.source_id,
#         )
#
#         return TranslationOutput(**result)
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")
#
#
# @app.get("/api/v2/graph/relations/{concept}", tags=["Router"])
# async def get_concept_relations(
#     concept: str, depth: int = 2
# ) -> dict[str, Any]:
#     """
#     Get relationships for a concept from the knowledge graph
#
#     Args:
#         concept: Concept name (e.g., "photosynthesis")
#         depth: Depth of traversal (default: 2)
#
#     Returns:
#         List of related concepts with relationship types
#     """
#     from src.services.router_engine import router_engine
#
#     try:
#         relations = await router_engine.get_graph_relations(concept)
#
#         return {
#             "concept": concept,
#             "relations": relations,
#             "count": len(relations),
#         }
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Graph query error: {str(e)}")
#
#
# @app.get("/api/v2/router/health", tags=["Router"])
# async def router_health() -> dict[str, Any]:
#     """Check the health of the router engine"""
#     from src.services.router_engine import router_engine
#
#     health = await router_engine.health_check()
#     return health
#
#
# @app.get("/api/v2/graph/health", tags=["Router"])
# async def graph_health() -> dict[str, Any]:
#     """Check the health of the graph store"""
#     from src.services.graph_store import graph_store_service
#
#     health = await graph_store_service.health_check()
#     return health


# ============================================================================
# LibreTexts ADAPT API Endpoints
# ============================================================================

class ImportQuestionsInput(BaseModel):
    """Input for importing questions from OpenStax"""
    subject: Optional[str] = Field(None, description="Subject filter (biology, chemistry, etc.)")
    difficulty: Optional[str] = Field(None, description="Difficulty filter (elementary, middle, high, ap)")
    chapter: Optional[str] = Field(None, description="Chapter filter (e.g., '2.1', '5.2')")
    count: int = Field(10, ge=1, le=100, description="Number of questions to return")


class SearchQuestionsInput(BaseModel):
    """Input for searching imported questions"""
    query: str = Field(..., description="Search query")
    subject: Optional[str] = Field(None, description="Optional subject filter")
    topic: Optional[str] = Field(None, description="Optional topic filter")
    top_k: int = Field(5, ge=1, le=20, description="Number of results")


class QuestionOutput(BaseModel):
    """A question from the imported store"""
    question_id: str
    text: str
    subject: str
    topic: str
    difficulty: str
    type: str
    explanation: Optional[str]
    score: float


@app.post("/api/v1/adapt/import", response_model=dict[str, Any], tags=["ADAPT"])
async def import_questions(input_data: ImportQuestionsInput) -> dict[str, Any]:
    """
    Import questions from LibreTexts ADAPT into local vector store

    This endpoint:
    1. Fetches questions from ADAPT API (anonymized)
    2. Generates embeddings using local Ollama
    3. Stores questions in local SQLite vector store
    4. Returns import statistics

    FERPA Compliance:
    - All questions stored locally only
    - No PII sent to external APIs
    - Embeddings generated locally

    Example:
    ```json
    {
      "topic": "Photosynthesis",
      "subject": "Biology",
      "difficulty": "medium",
      "count": 50
    }
    ```
    """
    from src.services.openstax_import import openstax_importer
    from src.services.question_bank import (
        question_bank,
        Question,
        QuestionType,
        DifficultyLevel,
        Subject,
        QuestionBatch
    )

    try:
        pipeline = get_question_pipeline()

        result = await pipeline.import_topic_questions(
            topic=input_data.topic,
            subject=input_data.subject,
            difficulty=input_data.difficulty,
            count=input_data.count
        )

        return {
            "status": "success" if result.failed == 0 else "partial",
            "total_fetched": result.total_fetched,
            "successfully_imported": result.successfully_imported,
            "failed": result.failed,
            "errors": result.errors,
            "imported_ids": result.imported_ids,
            "duration_seconds": result.duration_seconds
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import error: {str(e)}")


@app.post("/api/v1/adapt/search", response_model=dict[str, Any], tags=["ADAPT"])
async def search_questions(input_data: SearchQuestionsInput) -> dict[str, Any]:
    """
    Search for similar questions in the local imported store

    This endpoint performs semantic search using the local vector store.
    No external API calls are made.

    Example:
    ```json
    {
      "query": "What is ATP?",
      "subject": "Biology",
      "top_k": 5
    }
    ```
    """
    from src.services.openstax_import import openstax_importer
    from src.services.question_bank import (
        question_bank,
        Question,
        QuestionType,
        DifficultyLevel,
        Subject,
        QuestionBatch
    )

    try:
        pipeline = get_question_pipeline()

        results = await pipeline.search_similar_questions(
            query=input_data.query,
            subject=input_data.subject,
            topic=input_data.topic,
            top_k=input_data.top_k
        )

        questions = []
        for result in results:
            metadata = result.get("metadata", {})
            questions.append(QuestionOutput(
                question_id=metadata.get("question_id", ""),
                text=result.get("content", ""),
                subject=metadata.get("subject", ""),
                topic=metadata.get("topic", ""),
                difficulty=metadata.get("difficulty", ""),
                type=metadata.get("question_type", ""),
                explanation=metadata.get("explanation"),
                score=result.get("score", 0.0)
            ))

        return {
            "query": input_data.query,
            "count": len(questions),
            "questions": questions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.get("/api/v1/adapt/topics", response_model=dict[str, Any], tags=["ADAPT"])
async def get_imported_topics(subject: Optional[str] = None) -> dict[str, Any]:
    """
    Get list of topics that have been imported from ADAPT

    Query Parameters:
    - subject: Optional subject filter (e.g., "Biology")

    Returns:
        List of imported topic names

    Example:
    ```json
    {
      "topics": ["Photosynthesis", "Cellular Respiration", "Genetics"],
      "count": 3,
      "subject": "Biology"
    }
    ```
    """
    from src.services.openstax_import import openstax_importer
    from src.services.question_bank import (
        question_bank,
        Question,
        QuestionType,
        DifficultyLevel,
        Subject,
        QuestionBatch
    )

    try:
        pipeline = get_question_pipeline()

        topics = await pipeline.get_imported_topics(subject=subject)

        return {
            "topics": topics,
            "count": len(topics),
            "subject": subject
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving topics: {str(e)}")


@app.get("/api/v1/adapt/statistics", response_model=dict[str, Any], tags=["ADAPT"])
async def get_question_statistics() -> dict[str, Any]:
    """
    Get statistics about imported questions

    Returns:
        Statistics including total count, breakdown by subject/topic/difficulty

    Example:
    ```json
    {
      "total": 150,
      "by_subject": {"Biology": 100, "Chemistry": 50},
      "by_topic": {"Photosynthesis": 30, "Genetics": 25},
      "by_difficulty": {"easy": 50, "medium": 75, "hard": 25}
    }
    ```
    """
    from src.services.openstax_import import openstax_importer
    from src.services.question_bank import (
        question_bank,
        Question,
        QuestionType,
        DifficultyLevel,
        Subject,
        QuestionBatch
    )

    try:
        pipeline = get_question_pipeline()

        stats = await pipeline.get_statistics()

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")


@app.get("/api/v1/adapt/health", response_model=dict[str, Any], tags=["ADAPT"])
async def adapt_health_check() -> dict[str, Any]:
    """
    Check the health of the ADAPT integration

    Returns:
        Health status including:
        - Local vector store status
        - ADAPT API availability (if configured)
        - Question import statistics
    """
    from src.services.openstax_import import openstax_importer
    from src.services.question_bank import (
        question_bank,
        Question,
        QuestionType,
        DifficultyLevel,
        Subject,
        QuestionBatch
    )
    from src.services.adapt_client import get_adapt_client

    try:
        # Check local pipeline
        pipeline = get_question_pipeline()
        stats = await pipeline.get_statistics()

        # Check ADAPT API (if configured)
        adapt_client = get_adapt_client()
        adapt_health = await adapt_client.health_check()

        return {
            "status": "healthy",
            "local_store": {
                "status": "available",
                "total_questions": stats.get("total", 0),
                "subjects": list(stats.get("by_subject", {}).keys()),
                "topics": list(stats.get("by_topic", {}).keys())
            },
            "adapt_api": adapt_health,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# ============================================================================
# OpenTDB API Endpoints (Free alternative to ADAPT)
# ============================================================================

class FetchQuestionsInput(BaseModel):
    """Input for fetching questions from OpenTDB"""
    amount: int = Field(10, ge=1, le=50, description="Number of questions (max 50)")
    category: Optional[int] = Field(None, description="Category ID (17=Science, 19=Math, etc.)")
    difficulty: Optional[str] = Field(None, description="Difficulty: easy, medium, hard")
    type: Optional[str] = Field(None, description="Question type: multiple, boolean")
    science_only: bool = Field(True, description="Only fetch science-related categories")


class QuestionOutput(BaseModel):
    """A question from OpenTDB"""
    id: str
    question: str
    correct_answer: str
    incorrect_answers: list[str]
    type: str
    difficulty: str
    category: str
    source: str


@app.post("/api/v1/opentdb/fetch", response_model=dict[str, Any], tags=["OpenTDB"])
async def fetch_opentdb_questions(input_data: FetchQuestionsInput) -> dict[str, Any]:
    """
    Fetch questions from OpenTDB (Free API, no key required)

    OpenTDB is a free, user-contributed trivia database with science questions.

    Categories:
    - 17: Science & Nature
    - 18: Science: Computers
    - 19: Science: Mathematics
    - 27: Animals
    - 30: Science: Gadgets

    Rate limit: 1 request per 5 seconds per IP
    Max questions: 50 per request

    Example:
    ```json
    {
      "amount": 10,
      "difficulty": "medium",
      "science_only": true
    }
    ```
    """
    from src.services.opentdb_client import get_opentdb_client

    try:
        client = get_opentdb_client()

        if input_data.science_only:
            # Fetch from science categories only
            questions = await client.get_science_questions(
                amount=input_data.amount,
                difficulty=input_data.difficulty
            )
        else:
            # Fetch from specified category
            questions = await client.get_questions(
                amount=input_data.amount,
                category=input_data.category,
                difficulty=input_data.difficulty,
                type=input_data.type
            )

        return {
            "count": len(questions),
            "questions": [
                QuestionOutput(
                    id=q.id,
                    question=q.question,
                    correct_answer=q.correct_answer,
                    incorrect_answers=q.incorrect_answers,
                    type=q.type,
                    difficulty=q.difficulty,
                    category=q.category,
                    source=q.source
                )
                for q in questions
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching questions: {str(e)}")


@app.get("/api/v1/opentdb/categories", response_model=dict[str, Any], tags=["OpenTDB"])
async def get_opentdb_categories() -> dict[str, Any]:
    """
    Get all available OpenTDB categories

    Returns:
        List of categories with IDs

    Example:
    ```json
    {
      "categories": [
        {"id": 17, "name": "Science & Nature"},
        {"id": 19, "name": "Science: Mathematics"}
      ]
    }
    ```
    """
    from src.services.opentdb_client import get_opentdb_client

    try:
        client = get_opentdb_client()
        categories = await client.get_categories()

        return {
            "categories": categories,
            "count": len(categories),
            "science_categories": {
                17: "Science & Nature",
                18: "Science: Computers",
                19: "Science: Mathematics",
                27: "Animals",
                30: "Science: Gadgets"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")


@app.get("/api/v1/opentdb/health", response_model=dict[str, Any], tags=["OpenTDB"])
async def opentdb_health_check() -> dict[str, Any]:
    """
    Check OpenTDB API availability

    Returns:
        Health status and API information
    """
    from src.services.opentdb_client import get_opentdb_client

    try:
        client = get_opentdb_client()
        health = await client.health_check()

        return health

    except Exception as e:
        return {
            "status": "unhealthy",
            "api_available": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/api/v1/opentdb/import", response_model=dict[str, Any], tags=["OpenTDB"])
async def import_opentdb_questions(input_data: FetchQuestionsInput) -> dict[str, Any]:
    """
    Import OpenTDB questions into local vector store

    This endpoint:
    1. Fetches questions from OpenTDB
    2. Generates embeddings using local Ollama
    3. Stores in local SQLite vector store
    4. Returns import statistics

    Example:
    ```json
    {
      "amount": 20,
      "difficulty": "medium",
      "science_only": true
    }
    ```
    """
    from src.services.opentdb_client import get_opentdb_client, OpenTDBQuestion
    from src.services.sqlite_vector_store import sqlite_vector_store

    try:
        client = get_opentdb_client()

        # Fetch questions
        if input_data.science_only:
            questions = await client.get_science_questions(
                amount=input_data.amount,
                difficulty=input_data.difficulty
            )
        else:
            questions = await client.get_questions(
                amount=input_data.amount,
                category=input_data.category,
                difficulty=input_data.difficulty,
                type=input_data.type
            )

        # Import to vector store
        imported_count = 0
        failed_count = 0

        for q in questions:
            try:
                # Generate embedding
                # Use the vector store's embed_text function
                embedding = await sqlite_vector_store.embed_text(q.question)

                if isinstance(embedding, list) and len(embedding) > 0:
                    vec = embedding[0]
                else:
                    continue

                # Store in vector store
                await sqlite_vector_store.add_texts(
                    texts=[q.question],
                    metadatas=[{
                        "type": "question",
                        "question_id": q.id,
                        "category": q.category,
                        "difficulty": q.difficulty,
                        "correct_answer": q.correct_answer,
                        "source": "opentdb"
                    }],
                    embeddings=[vec]
                )
                imported_count += 1

            except Exception as e:
                failed_count += 1
                continue

        return {
            "status": "success",
            "total_fetched": len(questions),
            "successfully_imported": imported_count,
            "failed": failed_count,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import error: {str(e)}")


# ============================================================================
# SciQ Dataset Import Endpoints
# ============================================================================

class SciQImportInput(BaseModel):
    """Input for importing SciQ dataset"""
    max_questions: Optional[int] = Field(None, ge=1, description="Maximum questions to import (None for all)")
    subjects: Optional[list[str]] = Field(None, description="Filter by subjects (e.g., ['Biology', 'Chemistry'])")


@app.post("/api/v1/datasets/sciq/import", response_model=dict[str, Any], tags=["Datasets"])
async def import_sciq_dataset(input_data: SciQImportInput) -> dict[str, Any]:
    """
    Import SciQ dataset from HuggingFace into Supabase

    SciQ Dataset:
    - 13,679 crowdsourced science exam questions
    - Covers Physics, Chemistry, Biology
    - Source: https://huggingface.co/datasets/allenai/sciq
    - License: Apache 2.0

    This endpoint:
    1. Downloads the SciQ dataset from HuggingFace
    2. Classifies questions by subject (Biology/Chemistry/Physics)
    3. Infers topics from question content
    4. Generates embeddings using local Ollama
    5. Stores questions in Supabase with pgvector

    Example:
    ```json
    {
      "max_questions": 1000,
      "subjects": ["Biology", "Chemistry"]
    }
    ```
    """
    from src.services.sciq_importer import import_sciq_dataset

    try:
        result = await import_sciq_dataset(
            max_questions=input_data.max_questions,
            subjects=input_data.subjects
        )

        return {
            "status": "success" if result.failed == 0 else "partial",
            "total_fetched": result.total_fetched,
            "successfully_imported": result.successfully_imported,
            "failed": result.failed,
            "errors": result.errors[:10],  # First 10 errors only
            "imported_ids": result.imported_ids[:10],  # First 10 IDs only
            "duration_seconds": result.duration_seconds,
            "dataset": "SciQ",
            "source": "HuggingFace"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SciQ import error: {str(e)}")


# ============================================================================
# National Science Bowl Import Endpoints
# ============================================================================

class ScienceBowlImportInput(BaseModel):
    """Input for importing National Science Bowl questions"""
    max_questions: Optional[int] = Field(None, ge=1, description="Maximum questions to import (None for all)")
    subjects: Optional[list[str]] = Field(None, description="Filter by subjects")
    level: Optional[str] = Field(None, description="Filter by level: 'middle_school', 'high_school'")


@app.post("/api/v1/datasets/science-bowl/import", response_model=dict[str, Any], tags=["Datasets"])
async def import_science_bowl_dataset(input_data: ScienceBowlImportInput) -> dict[str, Any]:
    """
    Import National Science Bowl questions from GitHub into Supabase

    National Science Bowl Questions:
    - 7,000+ official competition questions
    - Middle School and High School levels
    - All science categories
    - Source: https://github.com/arxenix/Scibowl_Questions
    - Public domain (US government)

    This endpoint:
    1. Downloads questions from GitHub repository
    2. Parses JSON question files
    3. Classifies by subject and infers topics
    4. Generates embeddings using local Ollama
    5. Stores questions in Supabase with pgvector

    Example:
    ```json
    {
      "max_questions": 500,
      "subjects": ["Physics", "Chemistry"],
      "level": "high_school"
    }
    ```
    """
    from src.services.science_bowl_importer import import_science_bowl_questions

    try:
        result = await import_science_bowl_questions(
            max_questions=input_data.max_questions,
            subjects=input_data.subjects,
            level=input_data.level
        )

        return {
            "status": "success" if result.failed == 0 else "partial",
            "total_fetched": result.total_fetched,
            "successfully_imported": result.successfully_imported,
            "failed": result.failed,
            "errors": result.errors[:10],  # First 10 errors only
            "imported_ids": result.imported_ids[:10],  # First 10 IDs only
            "duration_seconds": result.duration_seconds,
            "dataset": "National Science Bowl",
            "source": "GitHub"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Science Bowl import error: {str(e)}")


# ============================================================================
# Supabase Questions API Endpoints
# ============================================================================

class SupabaseQuestionSearchInput(BaseModel):
    """Input for searching questions in Supabase"""
    query: str = Field(..., description="Search query text")
    subject: Optional[str] = Field(None, description="Filter by subject")
    topic: Optional[str] = Field(None, description="Filter by topic")
    difficulty: Optional[str] = Field(None, description="Filter by difficulty")
    source: Optional[str] = Field(None, description="Filter by source (sciq, science_bowl, opentdb)")
    limit: int = Field(10, ge=1, le=50, description="Maximum results")
    threshold: float = Field(0.6, ge=0.0, le=1.0, description="Minimum similarity threshold")


@app.post("/api/v1/questions/search", response_model=dict[str, Any], tags=["Questions"])
async def search_supabase_questions(input_data: SupabaseQuestionSearchInput) -> dict[str, Any]:
    """
    Search for questions in Supabase using semantic vector search

    This endpoint performs semantic search on questions stored in Supabase
    using pgvector similarity. Results are ranked by similarity to the query.

    Example:
    ```json
    {
      "query": "What is photosynthesis?",
      "subject": "Biology",
      "limit": 10
    }
    ```
    """
    from src.services.supabase_vector_store import get_supabase_vector_store

    try:
        store = get_supabase_vector_store()

        results = await store.search_similar_questions(
            query=input_data.query,
            subject=input_data.subject,
            topic=input_data.topic,
            difficulty=input_data.difficulty,
            source=input_data.source,
            limit=input_data.limit,
            threshold=input_data.threshold
        )

        return {
            "query": input_data.query,
            "count": len(results),
            "results": [r.model_dump() for r in results]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.get("/api/v1/questions/random", response_model=dict[str, Any], tags=["Questions"])
async def get_random_supabase_questions(
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 10
) -> dict[str, Any]:
    """
    Get random questions from Supabase (useful for quizzes)

    Query Parameters:
    - subject: Filter by subject
    - topic: Filter by topic
    - difficulty: Filter by difficulty (easy, medium, hard)
    - source: Filter by source (sciq, science_bowl, opentdb)
    - limit: Maximum results (default: 10)

    Returns:
        List of random questions with answers
    """
    from src.services.supabase_vector_store import get_supabase_vector_store

    try:
        store = get_supabase_vector_store()

        questions = await store.get_random_questions(
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            source=source,
            limit=limit
        )

        return {
            "count": len(questions),
            "questions": [q.model_dump(exclude={"embedding"}) for q in questions]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching questions: {str(e)}")


@app.get("/api/v1/questions/statistics", response_model=dict[str, Any], tags=["Questions"])
async def get_questions_statistics() -> dict[str, Any]:
    """
    Get statistics about questions in Supabase

    Returns:
        Aggregate statistics grouped by source and subject

    Example:
    ```json
    {
      "by_source_subject": [
        {
          "source": "sciq",
          "subject": "Biology",
          "total_questions": 5000,
          "easy_count": 0,
          "medium_count": 5000,
          "hard_count": 0
        }
      ],
      "total_questions": 20000
    }
    ```
    """
    from src.services.supabase_vector_store import get_supabase_vector_store

    try:
        store = get_supabase_vector_store()
        stats = await store.get_statistics()

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")


@app.get("/api/v1/questions/topics", response_model=dict[str, Any], tags=["Questions"])
async def get_questions_topics(subject: Optional[str] = None) -> dict[str, Any]:
    """
    Get list of unique topics from imported questions

    Query Parameters:
    - subject: Optional subject filter

    Returns:
        List of topic names
    """
    from src.services.supabase_vector_store import get_supabase_vector_store

    try:
        store = get_supabase_vector_store()
        topics = await store.get_topics(subject=subject)

        return {
            "topics": topics,
            "count": len(topics),
            "subject": subject
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving topics: {str(e)}")


@app.get("/api/v1/questions/health", response_model=dict[str, Any], tags=["Questions"])
async def supabase_questions_health() -> dict[str, Any]:
    """
    Check the health of the Supabase questions system

    Returns:
        Health status including:
        - Vector store type (supabase_pgvector)
        - Embedding model info
        - Total questions count
        - Supabase connection status
    """
    from src.services.supabase_vector_store import get_supabase_vector_store

    try:
        store = get_supabase_vector_store()
        health = await store.health_check()

        return health

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "vector_store_type": "supabase_pgvector"
        }


# =============================================================================
# Phase D: Question Bank Endpoints (OpenStax Instructor Resources)
# =============================================================================

class QuestionBankSearchInput(BaseModel):
    """Input for searching question bank"""
    query: str = Field(..., description="Search query text")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")


class QuestionBankRandomInput(BaseModel):
    """Input for getting random questions"""
    count: int = Field(10, ge=1, le=50, description="Number of questions")
    subject: Optional[str] = Field(None, description="Filter by subject")
    difficulty: Optional[str] = Field(None, description="Filter by difficulty")
    chapter: Optional[str] = Field(None, description="Filter by chapter reference")


@app.post("/api/v1/questions/bank/search", response_model=dict[str, Any], tags=["Question Bank"])
async def search_question_bank(input_data: QuestionBankSearchInput) -> dict[str, Any]:
    """
    Search questions in question bank

    Performs full-text search across question stems, explanations,
    and chapter references.

    Example:
    ```json
    {
      "query": "cell membrane",
      "limit": 10
    }
    ```
    """
    try:
        results = await question_bank.search_questions(
            query=input_data.query,
            limit=input_data.limit
        )

        return {
            "query": input_data.query,
            "count": len(results),
            "questions": [
                {
                    "id": q.id,
                    "type": str(q.type.value) if hasattr(q.type, 'value') else str(q.type),
                    "subject": str(q.subject.value) if hasattr(q.subject, 'value') else str(q.subject),
                    "difficulty": str(q.difficulty.value) if hasattr(q.difficulty, 'value') else str(q.difficulty),
                    "stem": q.stem,
                    "chapter_ref": q.chapter_ref,
                    "section_ref": q.section_ref
                }
                for q in results
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.get("/api/v1/questions/bank/random", response_model=dict[str, Any], tags=["Question Bank"])
async def get_random_bank_questions(
    subject: Optional[str] = None,
    difficulty: Optional[str] = None,
    chapter: Optional[str] = None,
    count: int = 10
) -> dict[str, Any]:
    """
    Get random questions from question bank (useful for quizzes)

    Query Parameters:
    - subject: Filter by subject (e.g., "biology")
    - difficulty: Filter by difficulty (e.g., "middle")
    - chapter: Filter by chapter reference (e.g., "2.1")
    - count: Number of questions (default: 10, max: 50)
    """
    try:
        questions = await question_bank.get_random_questions(
            count=count,
            subject=subject,
            difficulty=difficulty,
            chapter=chapter
        )

        return {
            "count": len(questions),
            "questions": [
                {
                    "id": q.id,
                    "type": str(q.type.value) if hasattr(q.type, 'value') else str(q.type),
                    "subject": str(q.subject.value) if hasattr(q.subject, 'value') else str(q.subject),
                    "difficulty": str(q.difficulty.value) if hasattr(q.difficulty, 'value') else str(q.difficulty),
                    "stem": q.stem,
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                    "chapter_ref": q.chapter_ref,
                    "section_ref": q.section_ref
                }
                for q in questions
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching questions: {str(e)}")


@app.get("/api/v1/questions/bank/stats", response_model=dict[str, Any], tags=["Question Bank"])
async def get_question_bank_stats() -> dict[str, Any]:
    """
    Get question bank statistics

    Returns:
    - Total questions count
    - Questions by subject
    - Questions by difficulty
    - Chapters covered
    """
    try:
        stats = question_bank.get_stats()

        return {
            "status": "healthy",
            "service": "question_bank",
            "total_questions": stats["total_questions"],
            "by_subject": stats["by_subject"],
            "by_difficulty": stats["by_difficulty"],
            "chapters_covered": stats.get("chapters_covered", 0)
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/api/v1/questions/bank/health", response_model=dict[str, Any], tags=["Question Bank"])
async def question_bank_health() -> dict[str, Any]:
    """
    Check the health of the question bank service

    Returns:
    - Service status
    - Question count
    - Service type (question_bank)
    """
    try:
        stats = question_bank.get_stats()

        return {
            "status": "healthy",
            "service": "question_bank",
            "data_source": "OpenStax Instructor Resources",
            "storage": "in-memory",
            "total_questions": stats["total_questions"],
            "ferpa_compliant": True
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "question_bank",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
