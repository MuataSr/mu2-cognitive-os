"""
Mu2 Cognitive OS - Brain Package
FastAPI application with LangGraph state machine
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any, Dict
from datetime import datetime
import os

from src.graph.morning_circle import morning_circle_graph
from src.core.config import settings

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

    Flow: Input -> Sentiment Analysis -> Context Routing -> Retrieval -> Output
    """
    try:
        # Run the morning circle graph
        result = await morning_circle_graph.ainvoke(
            {"message": input_data.message, "mode": input_data.mode, "sources": [], "retrieved_context": {}}
        )

        return ChatOutput(**result)

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
