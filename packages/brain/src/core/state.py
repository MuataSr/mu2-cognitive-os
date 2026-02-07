"""
State definitions for Mu2 Cognitive OS
Shared state types used across the application
"""

from typing import TypedDict, Annotated, Literal, Any
from operator import add


class MorningCircleState(TypedDict):
    """State for the Morning Circle state machine"""

    message: str
    mode: str
    sentiment_score: float
    sentiment_label: str
    retrieval_type: Literal["fact", "concept"]
    response: str
    sources: Annotated[list[str], add]
    retrieved_context: dict[str, Any]
