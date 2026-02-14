"""
State definitions for Mu2 Cognitive OS
Shared state types used across the application
"""

from typing import TypedDict, Annotated, Literal, Any, Optional
from operator import add


class MorningCircleState(TypedDict):
    """State for the Morning Circle state machine"""

    # Input
    message: str
    mode: str
    user_id: Optional[str]

    # Anonymization (FERPA Compliance)
    original_message: Optional[str]  # Original before anonymization (in-memory only)
    anonymized_message: Optional[str]  # After PII removal
    anonymization_metadata: Optional[dict[str, Any]]  # What was removed

    # Sentiment Analysis
    sentiment_score: float
    sentiment_label: str

    # Context Routing
    retrieval_type: Literal["fact", "concept", "hybrid"]

    # Retrieval Results
    sources: Annotated[list[str], add]
    retrieved_context: dict[str, Any]

    # Knowledge Graph Results
    graph_concepts: Annotated[list[dict[str, Any]], add]  # Related concepts from graph
    graph_relationships: Annotated[list[dict[str, Any]], add]  # Concept relationships
    learning_path: Optional[list[str]]  # Suggested learning path
    prerequisites: Optional[list[str]]  # Required concepts for current query

    # Response Generation
    response: str

    # Citation Lock (Grounding Enforcement)
    citation_validated: Optional[bool]  # Whether citations were validated
    citation_lock: Optional[dict[str, Any]]  # Citation lock metadata
    citation_warning: Optional[str]  # Warning if validation failed

    # Hybrid LLM Routing Metadata
    llm_provider_used: Optional[str]  # "local" or "cloud"
    llm_routing_reason: Optional[str]  # Why this provider was chosen
    complexity_score: Optional[float]  # Query complexity (0-1)

    # Behavioral Signals (for adaptive UI)
    behavioral_signals: Optional[dict[str, Any]]  # Detected behavioral patterns
    suggested_mode: Optional[str]  # Suggested UI mode based on behavior
    urgency: Optional[Literal["none", "attention", "intervention"]]  # Intervention urgency

    # Learning Events (for mastery tracking)
    consecutive_errors: Optional[int]  # Consecutive incorrect answers
    time_spent_seconds: Optional[int]  # Time on current question
