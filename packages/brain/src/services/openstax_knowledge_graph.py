"""
OpenStax Knowledge Graph Service
=================================

Builds and manages a knowledge graph from OpenStax textbook concepts.
Uses NetworkX for graph operations (can be upgraded to Apache AGE later).

The knowledge graph enables:
1. Concept prerequisite tracking
2. Learning path recommendations
3. Concept relationship exploration
4. Knowledge gap detection
"""

import logging
import json
import networkx as nx
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ConceptNode:
    """A concept node in the knowledge graph"""
    concept_id: str
    name: str
    description: str = ""
    chapter_id: str = ""
    book_id: str = ""
    chunk_ids: List[str] = field(default_factory=list)
    grade_level: int = 0
    subject: str = "government"
    definition: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConceptRelationship:
    """A relationship between two concepts"""
    source_id: str
    target_id: str
    relationship_type: str  # PREREQUISITE, RELATED_TO, PART_OF, EXAMPLE_OF, etc.
    strength: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class OpenStaxKnowledgeGraph:
    """
    Knowledge graph for OpenStax textbook concepts

    Stores concept relationships and enables:
    - Prerequisite chains
    - Learning path recommendations
    - Knowledge gap detection
    - Concept similarity through graph structure
    """

    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the knowledge graph

        Args:
            db_config: Optional database config for persistence
        """
        self.graph = nx.DiGraph()  # Directed graph for prerequisite relationships
        self.concepts: Dict[str, ConceptNode] = {}
        self.relationships: List[ConceptRelationship] = []
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 54322,
            'database': 'postgres',
            'user': 'postgres',
            'password': 'your-super-secret-and-long-postgres-password'
        }

    def add_concept(self, concept: ConceptNode) -> bool:
        """
        Add a concept node to the graph

        Args:
            concept: ConceptNode to add

        Returns:
            True if added successfully
        """
        try:
            self.concepts[concept.concept_id] = concept
            self.graph.add_node(
                concept.concept_id,
                name=concept.name,
                description=concept.description,
                chapter_id=concept.chapter_id,
                book_id=concept.book_id,
                grade_level=concept.grade_level,
                subject=concept.subject
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add concept {concept.concept_id}: {e}")
            return False

    def add_relationship(self, relationship: ConceptRelationship) -> bool:
        """
        Add a relationship between two concepts

        Args:
            relationship: ConceptRelationship to add

        Returns:
            True if added successfully
        """
        try:
            # Validate that both concepts exist
            if relationship.source_id not in self.concepts:
                logger.warning(f"Source concept {relationship.source_id} not found")
                return False
            if relationship.target_id not in self.concepts:
                logger.warning(f"Target concept {relationship.target_id} not found")
                return False

            self.relationships.append(relationship)
            self.graph.add_edge(
                relationship.source_id,
                relationship.target_id,
                relationship_type=relationship.relationship_type,
                strength=relationship.strength,
                **relationship.metadata
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add relationship: {e}")
            return False

    def get_concept(self, concept_id: str) -> Optional[ConceptNode]:
        """Get a concept by ID"""
        return self.concepts.get(concept_id)

    def get_prerequisites(self, concept_id: str, depth: int = 3) -> List[ConceptNode]:
        """
        Get all prerequisites for a concept

        Args:
            concept_id: Concept to get prerequisites for
            depth: How many levels back to traverse

        Returns:
            List of prerequisite concepts
        """
        if concept_id not in self.graph:
            return []

        prereqs = []
        visited = set()

        # Traverse backwards using BFS
        from collections import deque
        queue = deque([(concept_id, 0)])

        while queue:
            current_id, current_depth = queue.popleft()

            if current_id in visited or current_depth >= depth:
                continue

            visited.add(current_id)

            # Get predecessors (prerequisites)
            for pred_id in self.graph.predecessors(current_id):
                if pred_id not in visited:
                    prereqs.append(self.concepts[pred_id])
                    queue.append((pred_id, current_depth + 1))

        return prereqs

    def get_learning_path(self, start_concept_id: str, end_concept_id: str) -> List[str]:
        """
        Find shortest learning path between two concepts

        Args:
            start_concept_id: Starting concept
            end_concept_id: Target concept

        Returns:
            List of concept IDs forming the path
        """
        try:
            path = nx.shortest_path(self.graph, start_concept_id, end_concept_id)
            return path
        except nx.NetworkXNoPath:
            return []

    def get_related_concepts(
        self,
        concept_id: str,
        relationship_type: Optional[str] = None,
        max_distance: int = 2
    ) -> List[Tuple[str, float]]:
        """
        Get concepts related to a given concept

        Args:
            concept_id: Starting concept
            relationship_type: Filter by relationship type
            max_distance: Maximum graph distance

        Returns:
            List of (concept_id, similarity_score) tuples
        """
        if concept_id not in self.graph:
            return []

        related = []

        # Use ego_graph to get neighbors within distance
        ego = nx.ego_graph(self.graph, concept_id, radius=max_distance)

        for node_id in ego.nodes():
            if node_id == concept_id:
                continue

            # Calculate similarity based on graph distance
            try:
                distance = nx.shortest_path_length(self.graph, concept_id, node_id)
                similarity = 1.0 / (1.0 + distance)  # Decay with distance

                # Filter by relationship type if specified
                if relationship_type:
                    edge_data = self.graph.get_edge_data(concept_id, node_id)
                    if edge_data and edge_data.get('relationship_type') == relationship_type:
                        related.append((node_id, similarity))
                else:
                    related.append((node_id, similarity))
            except nx.NetworkXNoPath:
                pass

        # Sort by similarity descending
        related.sort(key=lambda x: x[1], reverse=True)
        return related

    def detect_knowledge_gaps(self, learned_concepts: Set[str]) -> List[ConceptNode]:
        """
        Detect concepts that should be learned next

        Args:
            learned_concepts: Set of concept IDs the user has mastered

        Returns:
            List of recommended concepts to learn next
        """
        recommendations = []

        for concept_id in learned_concepts:
            # Get concepts that this concept enables
            for successor_id in self.graph.successors(concept_id):
                if successor_id not in learned_concepts:
                    # Check if all prerequisites are met
                    prereqs = self.get_prerequisites(successor_id, depth=1)
                    prereq_ids = {c.concept_id for c in prereqs}

                    if prereq_ids.issubset(learned_concepts):
                        recommendations.append(self.concepts[successor_id])

        # Remove duplicates and sort by "readiness" (fewest remaining prerequisites)
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec.concept_id not in seen:
                seen.add(rec.concept_id)
                unique_recommendations.append(rec)

        return unique_recommendations

    def build_from_embeddings(self, embeddings_file: Path) -> int:
        """
        Build knowledge graph from OpenStax embeddings JSON

        Args:
            embeddings_file: Path to embeddings JSON file

        Returns:
            Number of concepts added
        """
        logger.info(f"Building knowledge graph from {embeddings_file}")

        with open(embeddings_file, 'r') as f:
            data = json.load(f)

        chunks = data.get("chunks", [])
        concept_counter = 0
        relationship_counter = 0

        # First pass: Add all concepts
        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            chapter_id = chunk["chapter_id"]
            book_id = chunk["book_id"]
            key_concepts = chunk.get("key_concepts", [])
            definitions = chunk.get("definitions", {})

            for i, concept_name in enumerate(key_concepts):
                # Clean concept name
                clean_name = concept_name.strip().replace("\n", " ")
                if len(clean_name) < 3:  # Skip too short
                    continue

                concept_id = f"{book_id}_{clean_name.lower().replace(' ', '_')}"

                # Check if concept already exists (merge if it does)
                if concept_id in self.concepts:
                    # Merge chunk_ids
                    existing = self.concepts[concept_id]
                    if chunk_id not in existing.chunk_ids:
                        existing.chunk_ids.append(chunk_id)
                    # Update definition if this one has one and existing doesn't
                    new_definition = definitions.get(concept_name)
                    if new_definition and not existing.definition:
                        existing.definition = new_definition
                    continue

                # Check if concept has a definition
                definition = definitions.get(concept_name)

                concept = ConceptNode(
                    concept_id=concept_id,
                    name=clean_name,
                    description=f"Concept from {chapter_id}",
                    chapter_id=chapter_id,
                    book_id=book_id,
                    chunk_ids=[chunk_id],
                    subject=self._infer_subject(book_id),
                    definition=definition
                )

                if self.add_concept(concept):
                    concept_counter += 1

        # Second pass: Create relationships
        # Strategy: Concepts in same chunk are RELATED_TO
        # Concepts in earlier chapters are PREREQUISITE for later chapters
        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            chapter_id = chunk["chapter_id"]
            book_id = chunk["book_id"]
            chunk_concepts = chunk.get("key_concepts", [])

            # Extract chapter number
            chapter_num = self._extract_chapter_number(chapter_id)

            # Concepts in same chunk are related
            for i, concept1 in enumerate(chunk_concepts):
                for j, concept2 in enumerate(chunk_concepts):
                    if i >= j:
                        continue

                    id1 = f"{book_id}_{concept1.strip().lower().replace(' ', '_')}"
                    id2 = f"{book_id}_{concept2.strip().lower().replace(' ', '_')}"

                    if id1 in self.concepts and id2 in self.concepts:
                        rel = ConceptRelationship(
                            source_id=id1,
                            target_id=id2,
                            relationship_type="RELATED_TO",
                            strength=0.8,
                            metadata={"source_chunk": chunk_id}
                        )
                        if self.add_relationship(rel):
                            relationship_counter += 1

        logger.info(f"✓ Added {concept_counter} new concepts")
        logger.info(f"✓ Added {relationship_counter} new relationships")

        return concept_counter

    def save_to_database(self) -> bool:
        """
        Save knowledge graph to PostgreSQL

        Creates tables:
        - knowledge_graph_concepts: Concept nodes
        - knowledge_graph_relationships: Edges between concepts

        Returns:
            True if successful
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # Create concepts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_graph_concepts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    chapter_id TEXT,
                    book_id TEXT,
                    chunk_ids JSONB DEFAULT '[]'::jsonb,
                    grade_level INTEGER DEFAULT 0,
                    subject TEXT,
                    definition TEXT,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            # Create relationships table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_graph_relationships (
                    id BIGSERIAL PRIMARY KEY,
                    source_id TEXT NOT NULL REFERENCES knowledge_graph_concepts(id),
                    target_id TEXT NOT NULL REFERENCES knowledge_graph_concepts(id),
                    relationship_type TEXT NOT NULL,
                    strength FLOAT DEFAULT 1.0,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(source_id, target_id, relationship_type)
                );
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_kg_concepts_name
                ON knowledge_graph_concepts(name);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_kg_concepts_subject
                ON knowledge_graph_concepts(subject);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_kg_relationships_source
                ON knowledge_graph_relationships(source_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_kg_relationships_target
                ON knowledge_graph_relationships(target_id);
            """)

            # Insert concepts
            concept_data = []
            for concept_id, concept in self.concepts.items():
                # Merge chunk_ids if concept already exists
                concept_data.append((
                    concept_id,
                    concept.name,
                    concept.description,
                    concept.chapter_id,
                    concept.book_id,
                    json.dumps(list(set(concept.chunk_ids))),  # Deduplicate chunk_ids
                    concept.grade_level,
                    concept.subject,
                    concept.definition,
                    json.dumps(concept.metadata)
                ))

            execute_values(
                cursor,
                """
                INSERT INTO knowledge_graph_concepts
                (id, name, description, chapter_id, book_id, chunk_ids, grade_level, subject, definition, metadata)
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    description = EXCLUDED.description,
                    chunk_ids = EXCLUDED.chunk_ids,
                    definition = EXCLUDED.definition,
                    metadata = EXCLUDED.metadata
                """,
                concept_data
            )

            # Insert relationships (deduplicate first)
            seen_relationships = set()
            relationship_data = []
            for rel in self.relationships:
                # Create unique key for deduplication
                key = (rel.source_id, rel.target_id, rel.relationship_type)
                if key not in seen_relationships:
                    seen_relationships.add(key)
                    relationship_data.append((
                        rel.source_id,
                        rel.target_id,
                        rel.relationship_type,
                        rel.strength,
                        json.dumps(rel.metadata)
                    ))

            execute_values(
                cursor,
                """
                INSERT INTO knowledge_graph_relationships
                (source_id, target_id, relationship_type, strength, metadata)
                VALUES %s
                ON CONFLICT (source_id, target_id, relationship_type) DO UPDATE SET
                    strength = EXCLUDED.strength,
                    metadata = EXCLUDED.metadata
                """,
                relationship_data
            )

            conn.commit()

            cursor.execute("SELECT COUNT(*) FROM knowledge_graph_concepts")
            concept_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM knowledge_graph_relationships")
            rel_count = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            logger.info(f"✓ Saved {concept_count} concepts to database")
            logger.info(f"✓ Saved {rel_count} relationships to database")

            return True

        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics"""
        return {
            "total_concepts": len(self.concepts),
            "total_relationships": len(self.relationships),
            "density": nx.density(self.graph),
            "is_connected": nx.is_weakly_connected(self.graph),
            "strongly_connected_components": nx.number_strongly_connected_components(self.graph),
        }

    def _infer_subject(self, book_id: str) -> str:
        """Infer subject from book ID"""
        if "government" in book_id.lower():
            return "government"
        elif "biology" in book_id.lower():
            return "biology"
        elif "math" in book_id.lower() or "algebra" in book_id.lower():
            return "mathematics"
        else:
            return "general"

    def _extract_chapter_number(self, chapter_id: str) -> int:
        """Extract chapter number from chapter ID"""
        import re
        match = re.search(r'chapter(\d+)', chapter_id.lower())
        if match:
            return int(match.group(1))
        return 0


def build_knowledge_graph_from_embeddings(
    embeddings_file: Path,
    save_to_db: bool = True
) -> OpenStaxKnowledgeGraph:
    """
    Build knowledge graph from embeddings file

    Args:
        embeddings_file: Path to embeddings JSON
        save_to_db: Whether to save to PostgreSQL

    Returns:
        OpenStaxKnowledgeGraph instance
    """
    kg = OpenStaxKnowledgeGraph()
    kg.build_from_embeddings(embeddings_file)

    if save_to_db:
        kg.save_to_database()

    return kg


if __name__ == "__main__":
    # Build knowledge graph from all OpenStax chapter embeddings
    from src.core.config import OPENSTAX_EMBEDDINGS_DIR

    logger.info("=" * 60)
    logger.info("Building OpenStax Knowledge Graph")
    logger.info("=" * 60)

    # Find all chapter embedding files
    embedding_files = sorted(OPENSTAX_EMBEDDINGS_DIR.glob("*_chapter*_embeddings.json"))

    if not embedding_files:
        logger.error(f"No chapter embedding files found in {OPENSTAX_EMBEDDINGS_DIR}")
        exit(1)

    logger.info(f"Found {len(embedding_files)} chapter embedding files")

    # Build knowledge graph from all chapters
    kg = OpenStaxKnowledgeGraph()

    for i, embedding_file in enumerate(embedding_files, 1):
        logger.info(f"\n[{i}/{len(embedding_files)}] Processing {embedding_file.name}...")
        kg.build_from_embeddings(embedding_file)

    # Save to database
    logger.info("\nSaving to database...")
    kg.save_to_database()

    # Display statistics
    logger.info("\nGraph Statistics:")
    stats = kg.get_statistics()
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # Example: Get prerequisites for a concept
    if kg.concepts:
        sample_concept = list(kg.concepts.keys())[0]
        logger.info(f"\nSample Concept: {kg.concepts[sample_concept].name}")
        prereqs = kg.get_prerequisites(sample_concept)
        logger.info(f"  Prerequisites: {[p.name for p in prereqs]}")

    logger.info("\n" + "=" * 60)
    logger.info("Knowledge Graph Build Complete")
    logger.info("=" * 60)
