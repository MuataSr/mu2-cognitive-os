"""
Retrieval Nodes for Morning Circle State Machine
Integrates vector store retrieval with LangGraph
"""

from typing import Dict, Any
from src.core.state import MorningCircleState
from src.services.sqlite_vector_store import sqlite_vector_store


async def retrieve_facts(state: MorningCircleState) -> MorningCircleState:
    """
    Retrieve specific, factual information from the vector store

    This node performs vector similarity search for concrete, specific information
    """
    query = state["message"]

    # Retrieve relevant facts
    facts = await sqlite_vector_store.retrieve_facts(query, top_k=5)

    # Format retrieved context
    if facts:
        fact_contexts = [f["content"] for f in facts]
        sources = [f["metadata"].get("source", "unknown") for f in facts if f["metadata"].get("source")]

        # Store retrieved context in state
        state["sources"] = list(set(sources))  # Remove duplicates

        # Add retrieved context to state for response generation
        state["retrieved_context"] = {
            "type": "fact",
            "results": fact_contexts,
            "count": len(facts),
            "avg_score": sum(f["score"] for f in facts) / len(facts),
        }
    else:
        state["retrieved_context"] = {"type": "fact", "results": [], "count": 0, "avg_score": 0.0}
        state["sources"] = []

    return state


async def retrieve_concepts(state: MorningCircleState) -> MorningCircleState:
    """
    Retrieve abstract, conceptual information from the vector store

    This node performs broader vector search for theoretical explanations
    """
    query = state["message"]

    # Retrieve relevant concepts
    concepts = await sqlite_vector_store.retrieve_concepts(query, top_k=5)

    # Format retrieved context
    if concepts:
        concept_contexts = [c["content"] for c in concepts]
        sources = [c["metadata"].get("source", "unknown") for c in concepts if c["metadata"].get("source")]

        # Store retrieved context in state
        state["sources"] = list(set(sources))  # Remove duplicates

        # Add retrieved context to state for response generation
        state["retrieved_context"] = {
            "type": "concept",
            "results": concept_contexts,
            "count": len(concepts),
            "avg_score": sum(c["score"] for c in concepts) / len(concepts),
        }
    else:
        state["retrieved_context"] = {"type": "concept", "results": [], "count": 0, "avg_score": 0.0}
        state["sources"] = []

    return state


async def route_retrieval(state: MorningCircleState) -> MorningCircleState:
    """
    Route to appropriate retrieval function based on retrieval_type

    This node decides whether to use fact or concept retrieval
    based on the routing decision made earlier
    """
    retrieval_type = state.get("retrieval_type", "fact")

    if retrieval_type == "fact":
        return await retrieve_facts(state)
    else:
        return await retrieve_concepts(state)


async def generate_response_with_context(state: MorningCircleState) -> MorningCircleState:
    """
    Generate response using retrieved context from vector store

    This node uses the retrieved chunks to provide informed responses
    """
    sentiment = state["sentiment_label"]
    retrieval_type = state["retrieval_type"]
    mode = state["mode"]
    retrieved_context = state.get("retrieved_context", {})

    # Build response based on retrieved context
    if retrieved_context.get("results"):
        # We have relevant retrieved information
        context_count = retrieved_context.get("count", 0)
        avg_score = retrieved_context.get("avg_score", 0.0)

        if retrieval_type == "fact":
            response = f"Based on my knowledge base, I found {context_count} relevant fact(s) for your query (relevance: {avg_score:.2f}). "
            # Include top result
            if retrieved_context["results"]:
                response += f"Here's what I found: {retrieved_context['results'][0][:200]}..."
        else:
            response = f"I've analyzed {context_count} related concepts from my knowledge base (relevance: {avg_score:.2f}). "
            # Include top result
            if retrieved_context["results"]:
                response += f"Key concept: {retrieved_context['results'][0][:200]}..."
    else:
        # No relevant information found
        if retrieval_type == "fact":
            response = "I couldn't find specific facts matching your query in my knowledge base. This might be new information that needs to be added."
        else:
            response = "I don't have conceptual information about this topic in my knowledge base yet. Consider adding this concept for future reference."

    # Adjust response based on sentiment
    if sentiment == "negative":
        response = f"I understand this might be frustrating. {response}"
    elif sentiment == "positive":
        response = f"Great question! {response}"

    state["response"] = response

    return state
