"""
Retrieval Nodes for Morning Circle State Machine
Integrates vector store retrieval with LangGraph and Hybrid LLM Router
"""

from typing import Dict, Any, Optional
from src.core.state import MorningCircleState
from src.core.config import settings
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

    This node uses the retrieved chunks and optionally the hybrid LLM router
    to provide informed responses.

    CRITICAL: Enforces citation lock - all responses must include source citations.
    """
    from src.services.hybrid_llm_router import hybrid_router, LLMPurpose

    sentiment = state["sentiment_label"]
    retrieval_type = state["retrieval_type"]
    mode = state["mode"]
    retrieved_context = state.get("retrieved_context", {})
    message = state.get("message", "")
    user_id = state.get("user_id")
    sources = state.get("sources", [])

    # Check if we should use hybrid LLM routing
    use_hybrid_llm = settings.llm_hybrid_mode

    # Build context string
    context_str = ""
    if retrieved_context.get("results"):
        context_count = retrieved_context.get("count", 0)
        avg_score = retrieved_context.get("avg_score", 0.0)
        context_results = retrieved_context["results"]

        if context_results:
            context_str = "\n\n".join([f"- {ctx}" for ctx in context_results[:3]])

    # Generate response
    if use_hybrid_llm and context_str:
        # Use hybrid LLM router for intelligent response generation
        try:
            # Build prompt with citation requirement
            prompt = f"""You are a helpful educational assistant. Answer the student's question using the provided context.

Context from knowledge base:
{context_str}

Available sources: {', '.join(sources) if sources else 'None'}

Student's question: {message}

IMPORTANT: Your response must be grounded in the provided context. Reference specific sources when making claims.
Provide a clear, educational response. If the context doesn't fully answer the question, acknowledge that."""

            llm_response = await hybrid_router.generate(
                query=prompt,
                purpose=LLMPurpose.GENERATION,
                user_id=user_id,
                max_tokens=500,
                temperature=0.7
            )

            response = llm_response.text

            # Store routing metadata
            routing = llm_response.raw_response.get("routing_decision", {}) if llm_response.raw_response else {}
            state["llm_provider_used"] = routing.get("provider", "unknown")
            state["llm_routing_reason"] = routing.get("reason", "")
            state["complexity_score"] = routing.get("complexity_score", 0.0)

        except Exception as e:
            # Fallback to template-based response
            response = _generate_template_response(retrieved_context, retrieval_type, sentiment, sources)
            state["llm_provider_used"] = "fallback"
            state["llm_routing_reason"] = f"LLM error: {str(e)}"
    else:
        # Use template-based response
        response = _generate_template_response(retrieved_context, retrieval_type, sentiment, sources)
        state["llm_provider_used"] = "template"

    # ENFORCE CITATION LOCK
    # Validate that response has proper citations before returning
    try:
        from src.services.citation_lock import citation_lock_service
        citation_lock = citation_lock_service.enforce_citation_lock(
            response=response,
            sources=sources,
            retrieved_context=retrieved_context,
            allow_uncited=False  # STRICT: Require citations
        )
        state["citation_validated"] = True
        state["citation_lock"] = {
            "validated": citation_lock.validated,
            "citation_count": len(citation_lock.citations),
            "disclaimer": citation_lock.disclaimer
        }
    except ValueError as e:
        # Citation validation failed - add warning to response
        state["citation_validated"] = False
        state["citation_warning"] = str(e)
        # For now, still return the response but mark as unvalidated
        # In production, you might want to refuse to respond

    state["response"] = response
    return state


def _generate_template_response(
    retrieved_context: Dict[str, Any],
    retrieval_type: str,
    sentiment: str,
    sources: list = None
) -> str:
    """Generate a template-based response when LLM is not used"""
    if sources is None:
        sources = []

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

        # Add source citations
        if sources:
            response += f"\n\nSources: {', '.join(sources[:3])}"

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

    return response
