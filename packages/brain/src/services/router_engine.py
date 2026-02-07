"""
Router Engine for Mu2 Cognitive OS
Uses LlamaIndex Router to direct queries between Vector (facts) and Graph (concepts)
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Literal
from llama_index.core import VectorStoreIndex
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.llms.ollama import Ollama

from src.services.sqlite_vector_store import sqlite_vector_store
from src.core.config import settings


class GraphQueryEngine:
    """Custom query engine for graph-based concept retrieval"""

    def __init__(self, graph_service):
        self.graph_service = graph_service

    async def query(self, query_str: str) -> str:
        """
        Query the graph for concept relationships

        Args:
            query_str: Query string

        Returns:
            Formatted result string
        """
        await self.graph_service.ensure_initialized()

        # Extract key terms from query
        terms = self._extract_concept_terms(query_str)

        results = []
        for term in terms:
            # Search for concepts
            concepts = await self.graph_service.search_concepts(term)
            for concept in concepts:
                # Get relationships
                relationships = await self.graph_service.get_concept_relationships(
                    concept["name"]
                )
                results.append(
                    {
                        "concept": concept,
                        "relationships": relationships,
                        "source_type": "graph",
                    }
                )

        # Format results
        if not results:
            return "No related concepts found in the knowledge graph."

        output = []
        for result in results[:3]:  # Limit to top 3
            concept = result["concept"]
            output.append(f"Concept: {concept['name']}")
            output.append(f"Description: {concept['description']}")
            output.append(f"Grade Level: {concept['grade_level']}")

            if result["relationships"]:
                output.append("\nRelated Concepts:")
                for rel in result["relationships"][:5]:
                    output.append(
                        f"  - {rel['target']} ({rel['relationship']}): "
                        f"{rel['description'][:100]}..."
                    )

            output.append("\n" + "-" * 50 + "\n")

        return "\n".join(output)

    def _extract_concept_terms(self, query: str) -> List[str]:
        """Extract potential concept terms from query"""
        # Simple extraction - look for important nouns
        stop_words = {
            "what",
            "is",
            "the",
            "a",
            "an",
            "how",
            "does",
            "do",
            "why",
            "when",
            "where",
            "relate",
            "relates",
            "to",
            "between",
            "and",
            "explain",
            "describe",
            "define",
            "list",
        }

        words = query.lower().split()
        terms = [w for w in words if w not in stop_words and len(w) > 3]

        return terms[:5]  # Limit to 5 terms


class VectorQueryEngine:
    """Custom query engine for vector-based fact retrieval"""

    def __init__(self, vector_service):
        self.vector_service = vector_service

    async def query(self, query_str: str) -> str:
        """
        Query the vector store for factual information

        Args:
            query_str: Query string

        Returns:
            Formatted result string
        """
        await self.vector_service.ensure_initialized()

        # Retrieve facts
        results = await self.vector_service.retrieve_facts(query_str, top_k=5)

        if not results:
            # Try hybrid search if no facts found
            results = await self.vector_service.retrieve_hybrid(query_str, top_k=5)

        # Format results
        if not results:
            return "No relevant information found in the knowledge base."

        output = []
        for i, result in enumerate(results, 1):
            output.append(f"Source {i}:")
            output.append(result["content"])
            output.append(f"Relevance: {result['score']:.2f}")
            if result.get("metadata", {}).get("source"):
                output.append(f"Source: {result['metadata']['source']}")
            output.append("\n" + "-" * 50 + "\n")

        return "\n".join(output)


class RouterEngine:
    """
    Main Router Engine - "The Librarian"
    Routes queries between Vector Store (facts) and Graph Store (concepts)
    """

    def __init__(self):
        self.vector_engine: Optional[VectorQueryEngine] = None
        self.graph_engine: Optional[GraphQueryEngine] = None
        self.router: Optional[RouterQueryEngine] = None
        self.llm: Optional[Ollama] = None
        self._initialized = False

    async def initialize(self):
        """Initialize the router engine"""
        if self._initialized:
            return

        # Initialize LLM for routing decisions
        self.llm = Ollama(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            request_timeout=120.0,
        )

        # Initialize query engines
        self.vector_engine = VectorQueryEngine(sqlite_vector_store)
        self.graph_engine = None  # Disabled - graph store requires Postgres

        # Create tools for the router
        vector_tool = QueryEngineTool(
            query_engine=self.vector_engine,
            metadata=ToolMetadata(
                name="vector_search",
                description=(
                    "Useful for answering factual questions like 'What is X?', "
                    "'Define X', 'List X'. Returns specific information from "
                    "textbook chunks and knowledge base."
                ),
            ),
        )

        # Note: graph_search disabled - using SQLite instead of Postgres
        tools = [vector_tool]

        # Create router with LLM-based selector
        self.router = RouterQueryEngine(
            selector=LLMSingleSelector.from_defaults(llm=self.llm),
            query_engine_tools=tools,
            verbose=True,
        )

        self._initialized = True

    async def ensure_initialized(self):
        """Ensure the engine is initialized"""
        if not self._initialized:
            await self.initialize()

    async def query(
        self, query_str: str, retrieve_mode: Optional[Literal["auto", "vector", "graph"]] = "auto"
    ) -> Dict[str, Any]:
        """
        Main query method - routes to appropriate engine

        Args:
            query_str: The user's query
            retrieve_mode: 'auto' for automatic routing, 'vector' or 'graph' to force

        Returns:
            Dictionary with query results and metadata
        """
        await self.ensure_initialized()

        # Determine query type for routing
        query_type = self._classify_query(query_str)

        # Route based on mode
        if retrieve_mode == "vector":
            result = await self.vector_engine.query(query_str)
            engine_used = "vector"
        elif retrieve_mode == "graph":
            result = await self.graph_engine.query(query_str)
            engine_used = "graph"
        else:
            # Use automatic routing
            try:
                response = self.router.query(query_str)
                result = str(response)
                engine_used = "auto_router"
            except Exception as e:
                # Fallback to manual routing
                if query_type == "concept":
                    result = await self.graph_engine.query(query_str)
                    engine_used = "graph_fallback"
                else:
                    result = await self.vector_engine.query(query_str)
                    engine_used = "vector_fallback"

        return {
            "query": query_str,
            "result": result,
            "engine_used": engine_used,
            "query_type": query_type,
        }

    def _classify_query(self, query: str) -> Literal["fact", "concept"]:
        """
        Classify query type for routing

        Args:
            query: Query string

        Returns:
            'fact' for factual queries, 'concept' for conceptual/relational queries
        """
        query_lower = query.lower()

        # Patterns indicating conceptual/relational queries
        conceptual_patterns = [
            "how does",
            "how do",
            "why does",
            "why do",
            "relate",
            "relationship",
            "connection",
            "compare",
            "difference",
            "affect",
            "effect",
            "influence",
            "impact",
            "depend",
            "prerequisite",
            "before",
            "after",
        ]

        # Patterns indicating factual queries
        factual_patterns = ["what is", "define", "list", "name", "identify"]

        # Check for conceptual patterns
        for pattern in conceptual_patterns:
            if pattern in query_lower:
                return "concept"

        # Check for factual patterns
        for pattern in factual_patterns:
            if pattern in query_lower:
                return "fact"

        # Default to factual for "what" questions
        if query_lower.startswith("what"):
            return "fact"

        # Default to conceptual for longer, complex queries
        if len(query.split()) > 10:
            return "concept"

        return "fact"

    async def translate_to_grade_level(
        self,
        college_text: str,
        grade_level: int,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        "The Translator" - Simplifies text to appropriate grade level

        Args:
            college_text: Advanced text to simplify
            grade_level: Target grade level (1-12)
            source_id: Source ID for citation

        Returns:
            Dictionary with simplified text, metaphor, and citation
        """
        await self.ensure_initialized()

        if not self.llm:
            raise RuntimeError("LLM not initialized")

        # Build translation prompt
        prompt = f"""You are a science tutor for {grade_level}th grade students.

Original text: {college_text}

Task:
1. Simplify this explanation for a {grade_level}th grader
2. Provide a real-world metaphor that helps understand the concept
3. Return ONLY valid JSON in this exact format (no markdown, no extra text):

{{
  "simplified": "your simplified explanation here",
  "metaphor": "your real-world metaphor here",
  "source_id": "{source_id or 'unknown'}",
  "confidence": 0.95,
  "key_terms": ["term1", "term2"]
}}

Important: Return ONLY the JSON object, nothing else.
"""

        try:
            # Call LLM
            response = await asyncio.to_thread(
                self.llm.complete,
                prompt,
            )

            # Parse response
            response_text = str(response).strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            elif response_text.startswith("json"):
                response_text = response_text[5:].strip()

            result = json.loads(response_text)

            # Ensure required fields
            if "source_id" not in result:
                result["source_id"] = source_id or "unknown"

            return result

        except json.JSONDecodeError as e:
            # Fallback if JSON parsing fails
            return {
                "simplified": college_text,  # Return original if translation fails
                "metaphor": "Think of this like building blocks - each piece helps you understand the bigger picture.",
                "source_id": source_id or "unknown",
                "confidence": 0.5,
                "key_terms": [],
                "error": f"Translation parsing failed: {str(e)}",
            }
        except Exception as e:
            return {
                "simplified": college_text,
                "metaphor": "This is like learning a new skill - it takes practice and patience.",
                "source_id": source_id or "unknown",
                "confidence": 0.3,
                "key_terms": [],
                "error": str(e),
            }

    async def get_graph_relations(
        self, concept: str
    ) -> List[Dict[str, Any]]:
        """
        Get concept relationships from the graph

        Args:
            concept: Concept name

        Returns:
            List of relationships
        """
        await self.ensure_initialized()
        return await graph_store_service.get_concept_relationships(concept)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the router engine

        Returns:
            Health status information
        """
        try:
            await self.ensure_initialized()

            return {
                "status": "healthy",
                "llm_configured": self.llm is not None,
                "vector_engine_configured": self.vector_engine is not None,
                "graph_engine_configured": self.graph_engine is not None,
                "router_configured": self.router is not None,
                "llm_model": settings.llm_model,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global singleton instance
router_engine = RouterEngine()
