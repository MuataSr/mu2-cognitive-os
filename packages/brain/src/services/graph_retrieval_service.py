"""
Graph Retrieval Service for LangGraph Integration
================================================

Provides knowledge graph retrieval capabilities for the Morning Circle
state machine. Integrates with the OpenStax knowledge graph for concept
relationship queries and learning path recommendations.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Set
import networkx as nx

from src.services.openstax_knowledge_graph import OpenStaxKnowledgeGraph, ConceptNode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphRetrievalService:
    """
    Service for retrieving information from the knowledge graph

    Provides:
    - Concept relationship queries
    - Learning path recommendations
    - Prerequisite checking
    - Knowledge gap detection
    """

    def __init__(self):
        self.knowledge_graph = OpenStaxKnowledgeGraph()
        self._initialized = False

    async def initialize(self):
        """Initialize the knowledge graph from database"""
        if self._initialized:
            return

        try:
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port=54322,
                database='postgres',
                user='postgres',
                password='your-super-secret-and-long-postgres-password'
            )
            cursor = conn.cursor()

            # Load concepts
            cursor.execute("SELECT * FROM knowledge_graph_concepts")
            for row in cursor.fetchall():
                chunk_ids = row[5] if row[5] else []
                if isinstance(chunk_ids, str):
                    chunk_ids = json.loads(chunk_ids)

                concept = ConceptNode(
                    concept_id=row[0],
                    name=row[1],
                    description=row[2] or "",
                    chapter_id=row[3] or "",
                    book_id=row[4] or "",
                    chunk_ids=chunk_ids,
                    grade_level=row[6] or 0,
                    subject=row[7] or "",
                    definition=row[8]
                )
                self.knowledge_graph.add_concept(concept)

            # Load relationships
            cursor.execute("SELECT source_id, target_id, relationship_type, strength, metadata FROM knowledge_graph_relationships")
            from src.services.openstax_knowledge_graph import ConceptRelationship
            for row in cursor.fetchall():
                metadata = row[4] if row[4] else {}
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)

                rel = ConceptRelationship(
                    source_id=row[0],
                    target_id=row[1],
                    relationship_type=row[2],
                    strength=row[3],
                    metadata=metadata
                )
                self.knowledge_graph.add_relationship(rel)

            cursor.close()
            conn.close()

            self._initialized = True
            logger.info(f"✓ Graph Retrieval Service initialized with {len(self.knowledge_graph.concepts)} concepts")

        except Exception as e:
            logger.error(f"Failed to initialize graph retrieval service: {e}")
            # Continue anyway - graph will be empty

    async def ensure_initialized(self):
        """Ensure the service is initialized"""
        if not self._initialized:
            await self.initialize()

    async def search_concepts(
        self,
        query: str,
        limit: int = 5,
        subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for concepts by name or description

        Args:
            query: Search query
            limit: Max results
            subject: Optional subject filter

        Returns:
            List of matching concepts
        """
        await self.ensure_initialized()

        query_lower = query.lower()
        results = []

        for concept_id, concept in self.knowledge_graph.concepts.items():
            # Filter by subject if specified
            if subject and concept.subject != subject:
                continue

            # Search in name and description
            if (query_lower in concept.name.lower() or
                query_lower in concept.description.lower()):
                results.append({
                    "concept_id": concept.concept_id,
                    "name": concept.name,
                    "description": concept.description,
                    "subject": concept.subject,
                    "definition": concept.definition
                })

                if len(results) >= limit:
                    break

        return results

    async def get_related_concepts(
        self,
        concept_name: str,
        max_distance: int = 2,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get concepts related to a given concept

        Args:
            concept_name: Name of the concept
            max_distance: Maximum graph distance
            relationship_type: Filter by relationship type

        Returns:
            List of related concepts with similarity scores
        """
        await self.ensure_initialized()

        # Find concept ID by name
        concept_id = None
        for cid, concept in self.knowledge_graph.concepts.items():
            if concept.name.lower() == concept_name.lower():
                concept_id = cid
                break

        if not concept_id:
            return []

        # Get related concepts
        related = self.knowledge_graph.get_related_concepts(
            concept_id,
            relationship_type=relationship_type,
            max_distance=max_distance
        )

        results = []
        for related_id, similarity in related:
            concept = self.knowledge_graph.get_concept(related_id)
            if concept:
                results.append({
                    "concept_id": concept.concept_id,
                    "name": concept.name,
                    "description": concept.description,
                    "similarity": similarity,
                    "definition": concept.definition
                })

        return results

    async def get_prerequisites(
        self,
        concept_name: str,
        depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get prerequisites for a concept

        Args:
            concept_name: Name of the concept
            depth: How many levels back to traverse

        Returns:
            List of prerequisite concepts
        """
        await self.ensure_initialized()

        # Find concept ID by name
        concept_id = None
        for cid, concept in self.knowledge_graph.concepts.items():
            if concept.name.lower() == concept_name.lower():
                concept_id = cid
                break

        if not concept_id:
            return []

        prereqs = self.knowledge_graph.get_prerequisites(concept_id, depth=depth)

        return [
            {
                "concept_id": p.concept_id,
                "name": p.name,
                "description": p.description,
                "definition": p.definition
            }
            for p in prereqs
        ]

    async def get_learning_path(
        self,
        start_concept: str,
        end_concept: str
    ) -> List[str]:
        """
        Find shortest learning path between two concepts

        Args:
            start_concept: Starting concept name
            end_concept: Target concept name

        Returns:
            List of concept names forming the path
        """
        await self.ensure_initialized()

        # Find concept IDs
        start_id = None
        end_id = None
        for cid, concept in self.knowledge_graph.concepts.items():
            if concept.name.lower() == start_concept.lower():
                start_id = cid
            if concept.name.lower() == end_concept.lower():
                end_id = cid

        if not start_id or not end_id:
            return []

        # Get path
        path_ids = self.knowledge_graph.get_learning_path(start_id, end_id)

        # Convert to names
        path_names = []
        for pid in path_ids:
            concept = self.knowledge_graph.get_concept(pid)
            if concept:
                path_names.append(concept.name)

        return path_names

    async def detect_knowledge_gaps(
        self,
        learned_concepts: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Detect concepts that should be learned next

        Args:
            learned_concepts: List of concept names the user has mastered

        Returns:
            List of recommended concepts to learn next
        """
        await self.ensure_initialized()

        # Convert concept names to IDs
        learned_set = set()
        for concept_name in learned_concepts:
            for cid, concept in self.knowledge_graph.concepts.items():
                if concept.name.lower() == concept_name.lower():
                    learned_set.add(cid)
                    break

        # Get recommendations
        recommendations = self.knowledge_graph.detect_knowledge_gaps(learned_set)

        return [
            {
                "concept_id": r.concept_id,
                "name": r.name,
                "description": r.description,
                "definition": r.definition
            }
            for r in recommendations
        ]

    async def extract_concepts_from_query(self, query: str) -> List[str]:
        """
        Extract potential concept names from a query

        Args:
            query: User query text

        Returns:
            List of concept names found in the query
        """
        await self.ensure_initialized()

        import re
        # Remove punctuation and convert to lowercase
        query_clean = re.sub(r'[^\w\s]', ' ', query.lower())
        query_words = set(query_clean.split())

        found_concepts = []

        # Check for concept names in the query
        for concept_id, concept in self.knowledge_graph.concepts.items():
            concept_name_lower = concept.name.lower()
            concept_words = set(concept_name_lower.split())

            # Single word concept - check exact match
            if len(concept_words) == 1:
                if concept_words.issubset(query_words):
                    found_concepts.append(concept.name)
            # Multi-word concept - check if all words appear in order
            else:
                # Create regex pattern for the phrase with word boundaries
                pattern = r'\b' + r'\s+'.join(re.escape(w) for w in concept_name_lower.split()) + r'\b'
                if re.search(pattern, query_clean):
                    found_concepts.append(concept.name)

        return found_concepts


# Global singleton instance
graph_retrieval_service = GraphRetrievalService()
