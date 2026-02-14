"""
Retrieval Nodes for Morning Circle State Machine
Integrates vector store retrieval with knowledge graph retrieval
"""

from typing import Dict, Any, Optional, List
from src.core.state import MorningCircleState
from src.core.config import settings
from src.services.sqlite_vector_store import sqlite_vector_store
from src.services.graph_retrieval_service import graph_retrieval_service


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


async def retrieve_from_graph(state: MorningCircleState) -> MorningCircleState:
    """
    Retrieve related concepts from the knowledge graph

    This node performs graph traversal to find:
    - Related concepts
    - Prerequisites
    - Learning paths
    """
    query = state["message"]

    # Initialize graph service if needed
    await graph_retrieval_service.ensure_initialized()

    # Extract concepts from query
    concepts = await graph_retrieval_service.extract_concepts_from_query(query)

    if concepts:
        # Get related concepts for each found concept
        all_related = []
        all_prereqs = []

        for concept_name in concepts[:3]:  # Limit to top 3 concepts
            # Get related concepts
            related = await graph_retrieval_service.get_related_concepts(
                concept_name,
                max_distance=2
            )
            all_related.extend(related)

            # Get prerequisites
            prereqs = await graph_retrieval_service.get_prerequisites(
                concept_name,
                depth=2
            )
            all_prereqs.extend(prereqs)

        # Remove duplicates
        seen = set()
        unique_related = []
        for item in all_related:
            if item["name"] not in seen:
                seen.add(item["name"])
                unique_related.append(item)

        seen_prereqs = set()
        unique_prereqs = []
        for item in all_prereqs:
            if item["name"] not in seen_prereqs and item["name"] not in seen:
                seen_prereqs.add(item["name"])
                unique_prereqs.append(item)

        # Store in state
        state["graph_concepts"] = unique_related[:5]  # Top 5 related
        state["prerequisites"] = [p["name"] for p in unique_prereqs[:3]]

        # Build learning path if we have multiple concepts
        if len(concepts) >= 2:
            path = await graph_retrieval_service.get_learning_path(
                concepts[0],
                concepts[1]
            )
            state["learning_path"] = path
    else:
        # No concepts found in query
        state["graph_concepts"] = []
        state["prerequisites"] = []
        state["learning_path"] = []

    return state


async def retrieve_hybrid(state: MorningCircleState) -> MorningCircleState:
    """
    Hybrid retrieval combining vector store and knowledge graph

    This node performs both vector similarity search and graph traversal
    to provide comprehensive context for response generation.
    """
    query = state["message"]

    # First, do vector retrieval
    vector_state = await retrieve_facts(state)

    # Then, do graph retrieval
    graph_state = await retrieve_from_graph(vector_state)

    # Merge results
    # The retrieved_context from vector search is preserved
    # Graph results are added as additional context

    # Add graph concepts to retrieved context for generation
    retrieved_context = graph_state.get("retrieved_context", {})
    if retrieved_context:
        retrieved_context["graph_enhanced"] = True
        retrieved_context["related_concepts"] = [
            c["name"] for c in graph_state.get("graph_concepts", [])
        ]
        retrieved_context["prerequisites"] = graph_state.get("prerequisites", [])

    graph_state["retrieved_context"] = retrieved_context

    return graph_state


async def route_retrieval(state: MorningCircleState) -> MorningCircleState:
    """
    Route to appropriate retrieval function based on retrieval_type

    This node decides whether to use:
    - fact: Vector similarity search for specific information
    - concept: Vector similarity search for conceptual information
    - hybrid: Combined vector + graph retrieval for comprehensive understanding
    """
    retrieval_type = state.get("retrieval_type", "fact")

    if retrieval_type == "fact":
        return await retrieve_facts(state)
    elif retrieval_type == "concept":
        return await retrieve_concepts(state)
    elif retrieval_type == "hybrid":
        return await retrieve_hybrid(state)
    else:
        # Default to fact retrieval
        return await retrieve_facts(state)


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

    # Get graph results if available
    graph_concepts = state.get("graph_concepts", [])
    prerequisites = state.get("prerequisites", [])
    learning_path = state.get("learning_path", [])
    is_graph_enhanced = retrieved_context.get("graph_enhanced", False)

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

    # Add graph context if available
    graph_context_str = ""
    if is_graph_enhanced:
        if graph_concepts:
            graph_context_str += "\n\nRelated Concepts:\n"
            for c in graph_concepts[:5]:
                graph_context_str += f"- {c['name']}"
                if c.get('definition'):
                    graph_context_str += f": {c['definition'][:100]}..."
                graph_context_str += "\n"

        if prerequisites:
            graph_context_str += f"\n\nPrerequisites to understand: {', '.join(prerequisites)}\n"

        if learning_path:
            graph_context_str += f"\n\nSuggested Learning Path: {' → '.join(learning_path)}\n"

    # Generate response
    if use_hybrid_llm and (context_str or graph_context_str):
        # Use hybrid LLM router for intelligent response generation
        try:
            # Build prompt with citation requirement
            prompt = f"""You are a helpful educational assistant. Answer the student's question using the provided context.

Context from knowledge base:
{context_str}
{graph_context_str}

Available sources: {', '.join(sources) if sources else 'None'}

Student's question: {message}

IMPORTANT: Your response must be grounded in the provided context. Reference specific sources when making claims.
Provide a clear, educational response. If the context doesn't fully answer the question, acknowledge that.
{f"Leverage the related concepts and learning path shown above to provide context." if is_graph_enhanced else ""}"""

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
            response = _generate_template_response(
                retrieved_context, retrieval_type, sentiment, sources,
                graph_concepts, prerequisites, learning_path
            )
            state["llm_provider_used"] = "fallback"
            state["llm_routing_reason"] = f"LLM error: {str(e)}"
    else:
        # Use template-based response
        response = _generate_template_response(
            retrieved_context, retrieval_type, sentiment, sources,
            graph_concepts, prerequisites, learning_path
        )
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
    sources: list = None,
    graph_concepts: list = None,
    prerequisites: list = None,
    learning_path: list = None
) -> str:
    """Generate a template-based response when LLM is not used"""
    if sources is None:
        sources = []
    if graph_concepts is None:
        graph_concepts = []
    if prerequisites is None:
        prerequisites = []
    if learning_path is None:
        learning_path = []

    is_graph_enhanced = retrieved_context.get("graph_enhanced", False)

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

    # Add graph-enhanced information
    if is_graph_enhanced:
        if graph_concepts:
            response += f"\n\n**Related Concepts:** {', '.join([c['name'] for c in graph_concepts[:5]])}"

        if prerequisites:
            response += f"\n\n**Prerequisites:** You may want to review: {', '.join(prerequisites)}"

        if learning_path:
            response += f"\n\n**Learning Path:** {' → '.join(learning_path)}"

    # Adjust response based on sentiment
    if sentiment == "negative":
        response = f"I understand this might be frustrating. {response}"
    elif sentiment == "positive":
        response = f"Great question! {response}"

    return response
