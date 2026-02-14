"""
Morning Circle State Machine
LangGraph implementation for Mu2 Cognitive OS

Flow: Input -> Anonymization -> Sentiment Analysis -> Context Routing -> Retrieval -> Output
"""

from langgraph.graph import StateGraph, END
from typing import Literal, Optional
from pydantic import BaseModel, Field
from src.core.state import MorningCircleState
from src.core.config import settings
from src.graph.retrieval_nodes import route_retrieval


# Sentiment Analysis Result
class SentimentResult(BaseModel):
    score: float = Field(..., ge=-1.0, le=1.0)
    label: Literal["positive", "neutral", "negative"]
    confidence: float


# Node 0: Anonymization (FERPA Compliance)
async def anonymize_input(state: MorningCircleState) -> MorningCircleState:
    """
    Anonymize PII from user input before any processing.

    This is the FIRST node in the pipeline for FERPA compliance.
    All PII is detected and removed before any LLM processing.
    """
    from src.services.anonymization_service import anonymization_service

    message = state.get("message", "")
    user_id = state.get("user_id")

    # Skip anonymization if disabled
    if not settings.llm_anonymization_enabled:
        state["original_message"] = message
        state["anonymized_message"] = message
        state["anonymization_metadata"] = None
        return state

    # Anonymize the message
    result = await anonymization_service.anonymize_text(
        text=message,
        user_id=user_id,
        include_metadata=True
    )

    # Store both original and anonymized versions
    state["original_message"] = message  # In-memory only, never logged
    state["anonymized_message"] = result.anonymized_text
    state["anonymization_metadata"] = result.metadata

    # Update message to use anonymized version for downstream processing
    state["message"] = result.anonymized_text

    return state


# Node 1: Sentiment Analysis
async def analyze_sentiment(state: MorningCircleState) -> MorningCircleState:
    """
    Analyze sentiment of user input

    TODO: Integrate actual sentiment analysis model
    Currently using a simple heuristic
    """
    message = state["message"].lower()

    # Simple heuristic-based sentiment
    positive_words = ["good", "great", "excellent", "love", "happy", "thank"]
    negative_words = ["bad", "terrible", "hate", "sad", "angry", "frustrated"]

    positive_count = sum(1 for word in positive_words if word in message)
    negative_count = sum(1 for word in negative_words if word in message)

    if positive_count > negative_count:
        score = min(0.8, 0.3 + positive_count * 0.1)
        label = "positive"
    elif negative_count > positive_count:
        score = max(-0.8, -0.3 - negative_count * 0.1)
        label = "negative"
    else:
        score = 0.0
        label = "neutral"

    state["sentiment_score"] = score
    state["sentiment_label"] = label

    return state


# Node 2: Context Router (Fact vs Concept vs Hybrid)
async def route_context(state: MorningCircleState) -> MorningCircleState:
    """
    Route between Fact, Concept, and Hybrid retrieval

    Facts: Specific, concrete information → Vector search only
    Concepts: Abstract, theoretical explanations → Vector search only
    Hybrid: Complex queries requiring both content and relationships → Vector + Graph search

    Hybrid triggers:
    - "relationship" queries (how is X related to Y)
    - "prerequisite" queries (what should I learn before X)
    - "learning path" queries
    - Multi-concept queries
    - Comparison queries
    """
    message = state["message"].lower()
    words = message.split()

    # Hybrid indicators (check FIRST - most specific patterns)
    # These use word boundary matching to avoid partial matches
    hybrid_patterns = [
        # Relationship queries
        ("related to", "related"),
        ("relationship", "relationship"),
        ("connect", "connect"),
        # Prerequisite/learning path queries
        ("prerequisite", "prerequisite"),
        ("before learning", "before learning"),
        ("should i learn", "should i learn"),
        ("learn first", "learn first"),
        ("learning path", "learning path"),
        ("path to learn", "path to learn"),
        # Comparison queries
        ("compare", "compare"),
        ("difference between", "difference"),
        ("versus", "versus"),
        (" vs ", "vs"),
        ("similar to", "similar"),
        ("how do", "how do"),
    ]

    # Fact indicators (specific, concrete questions)
    # Use word boundaries to avoid matching "what should" as "what is"
    fact_patterns = [
        ("what is ", "what_is"),  # Note the space after "is"
        ("define ", "define"),
        ("who is ", "who"),
        ("who was ", "who"),
        ("when is ", "when"),
        ("when did ", "when"),
        ("where is ", "where"),
        ("how many", "how_many"),
        ("how much", "how_much"),
        ("list ", "list"),
    ]

    # Concept indicators (abstract, theoretical)
    concept_patterns = [
        ("explain ", "explain"),
        ("why does", "why"),
        ("why is", "why"),
        ("how does ", "how_does"),
        ("theory of", "theory"),
        ("analyze", "analyze"),
        ("describe", "describe"),
    ]

    # Check hybrid patterns FIRST (most specific)
    for pattern, _ in hybrid_patterns:
        if pattern in message:
            state["retrieval_type"] = "hybrid"
            state["routing_reason"] = f"hybrid_pattern: {pattern}"
            return state

    # Check fact patterns
    for pattern, name in fact_patterns:
        if pattern in message:
            state["retrieval_type"] = "fact"
            state["routing_reason"] = f"fact_pattern: {name}"
            return state

    # Check concept patterns
    for pattern, name in concept_patterns:
        if pattern in message:
            state["retrieval_type"] = "concept"
            state["routing_reason"] = f"concept_pattern: {name}"
            return state

    # Fallback: Analyze message complexity
    word_count = len(words)

    # Multiple clauses or complex sentences → hybrid
    if "," in message or word_count > 50:
        state["retrieval_type"] = "hybrid"
        state["routing_reason"] = "complex_query"
    # Longer queries → concept
    elif word_count > 15:
        state["retrieval_type"] = "concept"
        state["routing_reason"] = "long_query"
    # Short queries → fact
    else:
        state["retrieval_type"] = "fact"
        state["routing_reason"] = "short_query"

    return state


# Node 3: Generate Response (Legacy - replaced by retrieval_nodes.generate_response_with_context)
async def generate_response(state: MorningCircleState) -> MorningCircleState:
    """
    Generate the final response based on context and retrieval

    NOTE: This is now handled by generate_response_with_context in retrieval_nodes.py
    This function is kept for backwards compatibility
    """
    from src.graph.retrieval_nodes import generate_response_with_context

    return await generate_response_with_context(state)


# Node 4: Behavioral Analysis
async def analyze_behavior(state: MorningCircleState) -> MorningCircleState:
    """
    Detect behavioral signals for adaptive UI triggering

    This node analyzes:
    - Recent learning events (errors, time spent)
    - User sentiment
    - Suggests appropriate UI mode based on behavioral state

    Input: Recent learning events, time spent, sentiment
    Output: state["behavioral_signals"] = {...}
    """
    from src.services.behavioral_detector import behavioral_detector, LearningEvent

    user_id = state.get("user_id", "anonymous")
    sentiment = state.get("sentiment_label", "neutral")
    mode = state.get("mode", "standard")

    # Get behavioral signals
    # In a full implementation, these would come from a database
    # For now, we use simple heuristics based on sentiment

    # Create mock learning events based on sentiment
    # If sentiment is negative, assume some struggles
    mock_events = []
    if sentiment == "negative":
        # Simulate a struggling user
        mock_events.append(LearningEvent(
            user_id=user_id,
            skill_id="current",
            is_correct=False,
            attempts=3,
            time_spent_seconds=180
        ))
        state["consecutive_errors"] = 1

    # Analyze behavioral signals
    try:
        signals = await behavioral_detector.analyze_behavioral_signals(
            user_id=user_id,
            learning_events=mock_events,
            clickstream=[],  # Would come from frontend
            time_on_task_seconds=60  # Default
        )

        # Store signals in state
        state["behavioral_signals"] = {
            "is_frustrated": signals.is_frustrated,
            "is_engaged": signals.is_engaged,
            "is_struggling": signals.is_struggling,
            "confidence": signals.confidence,
            "reasoning": signals.reasoning
        }

        # Update mode based on behavioral signals
        state["suggested_mode"] = signals.suggested_mode
        state["urgency"] = signals.urgency

        # Override mode if urgent intervention needed
        if signals.urgency == "intervention":
            state["mode"] = "high_contrast_focus"
        elif signals.suggested_mode != mode:
            # Suggest mode change but don't force it
            state["mode"] = signals.suggested_mode

    except Exception as e:
        # Fallback to simple mode suggestion
        state["suggested_mode"] = mode
        state["urgency"] = "none"
        state["behavioral_signals"] = {"error": str(e)}

    return state


# Node 5: Suggest Mode (Legacy - kept for compatibility)
async def suggest_mode(state: MorningCircleState) -> MorningCircleState:
    """
    Suggest UI mode based on context

    Focus mode: For complex, lengthy content
    Standard mode: For quick interactions

    NOTE: This is now primarily handled by analyze_behavior
    This function is kept for backwards compatibility
    """
    word_count = len(state["message"].split())
    is_complex = word_count > 50 or state["retrieval_type"] == "concept"

    # Update mode if content is complex
    if is_complex and state["mode"] == "standard":
        state["mode"] = "focus"

    return state


# Build the State Graph
def build_morning_circle_graph() -> StateGraph:
    """Build and return the Morning Circle state machine"""

    # Create the graph
    workflow = StateGraph(MorningCircleState)

    # Add nodes
    workflow.add_node("anonymize", anonymize_input)  # FERPA compliance first!
    workflow.add_node("sentiment", analyze_sentiment)
    workflow.add_node("route", route_context)
    workflow.add_node("retrieve", route_retrieval)  # New retrieval node
    workflow.add_node("analyze_behavior", analyze_behavior)  # Behavioral detection
    workflow.add_node("generate", generate_response)
    workflow.add_node("suggest_mode", suggest_mode)  # Legacy, kept for compatibility

    # Define edges - Start with anonymization
    workflow.set_entry_point("anonymize")
    workflow.add_edge("anonymize", "sentiment")
    workflow.add_edge("sentiment", "route")
    workflow.add_edge("route", "retrieve")  # Route to retrieval
    workflow.add_edge("retrieve", "analyze_behavior")  # Behavioral analysis
    workflow.add_edge("analyze_behavior", "generate")  # Then to generation
    workflow.add_edge("generate", END)

    # Note: suggest_mode is kept but not in the main flow
    # It can be used separately if needed

    return workflow.compile()


# Compile the graph
morning_circle_graph = build_morning_circle_graph()
