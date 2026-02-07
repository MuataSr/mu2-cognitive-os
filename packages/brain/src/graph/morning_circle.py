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


# Node 2: Context Router (Fact vs Concept)
async def route_context(state: MorningCircleState) -> MorningCircleState:
    """
    Route between Fact and Concept retrieval

    Facts: Specific, concrete information
    Concepts: Abstract, theoretical explanations
    """
    message = state["message"].lower()

    # Heuristic: Question words often indicate factual queries
    fact_indicators = ["what is", "define", "who", "when", "where", "how many", "list"]
    concept_indicators = ["explain", "why", "how does", "relationship", "compare", "theory"]

    if any(indicator in message for indicator in fact_indicators):
        retrieval_type = "fact"
    elif any(indicator in message for indicator in concept_indicators):
        retrieval_type = "concept"
    else:
        # Default based on message length
        retrieval_type = "concept" if len(state["message"]) > 100 else "fact"

    state["retrieval_type"] = retrieval_type

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


# Node 4: Suggest Mode
async def suggest_mode(state: MorningCircleState) -> MorningCircleState:
    """
    Suggest UI mode based on context

    Focus mode: For complex, lengthy content
    Standard mode: For quick interactions
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
    workflow.add_node("generate", generate_response)
    workflow.add_node("suggest_mode", suggest_mode)

    # Define edges - Start with anonymization
    workflow.set_entry_point("anonymize")
    workflow.add_edge("anonymize", "sentiment")
    workflow.add_edge("sentiment", "route")
    workflow.add_edge("route", "retrieve")  # Route to retrieval
    workflow.add_edge("retrieve", "suggest_mode")  # Then to mode suggestion
    workflow.add_edge("suggest_mode", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


# Compile the graph
morning_circle_graph = build_morning_circle_graph()
