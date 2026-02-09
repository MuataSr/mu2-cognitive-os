"""
Test Hybrid Retrieval: Vector Store + Knowledge Graph
======================================================

Demonstrates how vector similarity search and knowledge graph traversal
work together to provide comprehensive learning support.

Use Cases:
1. FACT queries → Vector search (find exact content)
2. CONCEPT queries → Graph search (find relationships)
3. LEARNING PATH queries → Combined approach
"""

import logging
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.openstax_knowledge_graph import OpenStaxKnowledgeGraph
from scripts.test_semantic_search import SemanticSearchEngine, load_test_embeddings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HybridRetrievalEngine:
    """
    Combines vector similarity search with knowledge graph traversal

    Routes queries to the appropriate retrieval method:
    - Vector search: Facts, specific content, "what is X"
    - Graph search: Concepts, relationships, "how is X related to Y"
    - Hybrid: Learning paths, prerequisites, comprehensive understanding
    """

    def __init__(self):
        self.vector_search = SemanticSearchEngine()
        self.knowledge_graph = OpenStaxKnowledgeGraph()
        self._load_knowledge_graph()

    def _load_knowledge_graph(self):
        """Load knowledge graph from database"""
        # Load concepts from database
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
            from src.services.openstax_knowledge_graph import ConceptNode

            # Handle JSONB fields (already Python types from psycopg2)
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
            # Handle JSONB metadata
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

        logger.info(f"✓ Loaded {len(self.knowledge_graph.concepts)} concepts")
        logger.info(f"✓ Loaded {len(self.knowledge_graph.relationships)} relationships")

    def search(self, query_embedding, query_type: str = "auto", limit: int = 5):
        """
        Intelligent search routing

        Args:
            query_embedding: Query vector
            query_type: "fact", "concept", "path", or "auto"
            limit: Max results

        Returns:
            Search results with metadata
        """
        if query_type == "auto":
            # Auto-detect based on query characteristics
            query_type = self._classify_query(query_embedding)

        if query_type == "fact":
            return self._vector_search(query_embedding, limit)
        elif query_type == "concept":
            return self._graph_search(query_embedding, limit)
        elif query_type == "path":
            return self._learning_path_search(query_embedding, limit)
        else:
            return self._hybrid_search(query_embedding, limit)

    def _classify_query(self, query_embedding) -> str:
        """
        Classify query type (placeholder for future LLM-based classification)

        For now, defaults to "hybrid" to show both systems
        """
        return "hybrid"

    def _vector_search(self, query_embedding, limit: int):
        """Vector similarity search"""
        logger.info("→ Using Vector Search (pgvector)")
        results = self.vector_search.search_similar(
            query_embedding=query_embedding,
            limit=limit
        )
        return {
            "method": "vector",
            "results": results
        }

    def _graph_search(self, query_embedding, limit: int):
        """Knowledge graph search"""
        logger.info("→ Using Knowledge Graph Search")

        # Find similar chunk first to get concepts
        vector_results = self.vector_search.search_similar(
            query_embedding=query_embedding,
            limit=1
        )

        if not vector_results:
            return {"method": "graph", "results": []}

        # Get concepts from the chunk
        chunk = vector_results[0]
        concepts = chunk.get('key_concepts', [])

        if not concepts:
            return {"method": "graph", "results": []}

        # Get related concepts for the first concept
        concept_name = concepts[0]
        concept_id = f"american-government-3e_{concept_name.lower().replace(' ', '_')}"

        related = self.knowledge_graph.get_related_concepts(
            concept_id,
            max_distance=2
        )

        results = []
        for related_id, similarity in related[:limit]:
            concept = self.knowledge_graph.get_concept(related_id)
            if concept:
                results.append({
                    "concept_id": concept.concept_id,
                    "name": concept.name,
                    "description": concept.description,
                    "similarity": similarity,
                    "definition": concept.definition
                })

        return {
            "method": "graph",
            "seed_concept": concept_name,
            "results": results
        }

    def _learning_path_search(self, query_embedding, limit: int):
        """Find learning path through concepts"""
        logger.info("→ Using Learning Path Search")

        # Get start and end concepts
        vector_results = self.vector_search.search_similar(
            query_embedding=query_embedding,
            limit=3
        )

        paths = []
        for result in vector_results[:2]:
            concepts = result.get('key_concepts', [])
            if len(concepts) >= 2:
                from_id = f"american-government-3e_{concepts[0].lower().replace(' ', '_')}"
                to_id = f"american-government-3e_{concepts[1].lower().replace(' ', '_')}"

                path = self.knowledge_graph.get_learning_path(from_id, to_id)
                if path:
                    path_names = [
                        self.knowledge_graph.get_concept(pid).name
                        if self.knowledge_graph.get_concept(pid) else pid
                        for pid in path
                    ]
                    paths.append(path_names)

        return {
            "method": "learning_path",
            "paths": paths
        }

    def _hybrid_search(self, query_embedding, limit: int):
        """Combine vector and graph search"""
        logger.info("→ Using Hybrid Search (Vector + Graph)")

        # Get vector results
        vector_results = self.vector_search.search_similar(
            query_embedding=query_embedding,
            limit=limit
        )

        # Enhance with graph relationships
        enhanced_results = []
        for result in vector_results:
            concepts = result.get('key_concepts', [])

            # Get related concepts for each key concept
            related_concepts = []
            for concept_name in concepts[:3]:  # Limit to top 3
                concept_id = f"american-government-3e_{concept_name.lower().replace(' ', '_')}"
                related = self.knowledge_graph.get_related_concepts(
                    concept_id,
                    max_distance=1
                )
                for rel_id, rel_sim in related[:2]:  # Top 2 related
                    rel_concept = self.knowledge_graph.get_concept(rel_id)
                    if rel_concept:
                        related_concepts.append({
                            "name": rel_concept.name,
                            "similarity": rel_sim
                        })

            enhanced_results.append({
                **result,
                "related_concepts": related_concepts
            })

        return {
            "method": "hybrid",
            "results": enhanced_results
        }

    def get_knowledge_gaps(self, learned_concepts: list):
        """Get recommended next concepts based on what's been learned"""
        learned_set = set()
        for concept_name in learned_concepts:
            concept_id = f"american-government-3e_{concept_name.lower().replace(' ', '_')}"
            learned_set.add(concept_id)

        recommendations = self.knowledge_graph.detect_knowledge_gaps(learned_set)

        return [
            {
                "concept_id": c.concept_id,
                "name": c.name,
                "description": c.description
            }
            for c in recommendations
        ]

    def close(self):
        """Close connections"""
        self.vector_search.close()


def demonstrate_hybrid_retrieval():
    """Demonstrate hybrid retrieval system"""

    logger.info("=" * 70)
    logger.info("Hybrid Retrieval: Vector Store + Knowledge Graph")
    logger.info("=" * 70)

    # Initialize
    engine = HybridRetrievalEngine()

    # Load test embeddings
    logger.info("\nLoading test embeddings...")
    embeddings = load_test_embeddings()
    logger.info(f"✓ Loaded {len(embeddings)} embeddings")

    # Test 1: Vector Search (Fact Query)
    logger.info("\n" + "-" * 70)
    logger.info("Test 1: Vector Search - Finding Specific Content")
    logger.info("-" * 70)
    logger.info("Query: 'What is government?'")
    logger.info("Type: FACT query → Use vector search")

    test_embedding = embeddings["american-government-3e_chapter01_chunk_1"]
    results = engine.search(test_embedding, query_type="fact", limit=3)

    logger.info(f"\nResults ({results['method']}):")
    for i, r in enumerate(results['results'][:3], 1):
        logger.info(f"  {i}. {r['title'][:60]}...")
        logger.info(f"     Similarity: {r['similarity']:.4f}")

    # Test 2: Graph Search (Concept Query)
    logger.info("\n" + "-" * 70)
    logger.info("Test 2: Graph Search - Finding Related Concepts")
    logger.info("-" * 70)
    logger.info("Query: 'What concepts are related to government?'")
    logger.info("Type: CONCEPT query → Use knowledge graph")

    results = engine.search(test_embedding, query_type="concept", limit=5)

    if results.get('seed_concept'):
        logger.info(f"\nSeed concept: {results['seed_concept']}")
    logger.info(f"\nRelated concepts:")
    for i, r in enumerate(results.get('results', [])[:5], 1):
        logger.info(f"  {i}. {r['name']}")
        logger.info(f"     Similarity: {r['similarity']:.4f}")
        if r.get('definition'):
            logger.info(f"     Definition: {r['definition'][:80]}...")

    # Test 3: Hybrid Search (Comprehensive)
    logger.info("\n" + "-" * 70)
    logger.info("Test 3: Hybrid Search - Content + Relationships")
    logger.info("-" * 70)
    logger.info("Query: Comprehensive understanding with context")
    logger.info("Type: HYBRID → Vector results + Graph relationships")

    results = engine.search(test_embedding, query_type="hybrid", limit=2)

    logger.info(f"\nEnhanced results:")
    for i, r in enumerate(results.get('results', [])[:2], 1):
        logger.info(f"  {i}. {r['title'][:60]}...")
        logger.info(f"     Vector similarity: {r['similarity']:.4f}")
        logger.info(f"     Related concepts: {len(r.get('related_concepts', []))}")
        for rc in r.get('related_concepts', [])[:3]:
            logger.info(f"       - {rc['name']} ({rc['similarity']:.2f})")

    # Test 4: Knowledge Gaps
    logger.info("\n" + "-" * 70)
    logger.info("Test 4: Knowledge Gap Detection")
    logger.info("-" * 70)
    logger.info("Given learned concepts: ['government', 'democracy']")
    logger.info("What should be learned next?")

    recommendations = engine.get_knowledge_gaps(['government', 'democracy'])

    logger.info(f"\nRecommended next concepts:")
    for i, rec in enumerate(recommendations[:5], 1):
        logger.info(f"  {i}. {rec['name']}")
        logger.info(f"     {rec['description'][:60]}...")

    # Statistics
    logger.info("\n" + "-" * 70)
    logger.info("System Statistics")
    logger.info("-" * 70)

    kg_stats = engine.knowledge_graph.get_statistics()
    logger.info(f"\nKnowledge Graph:")
    logger.info(f"  Total concepts: {kg_stats['total_concepts']}")
    logger.info(f"  Total relationships: {kg_stats['total_relationships']}")
    logger.info(f"  Graph density: {kg_stats['density']:.4f}")
    logger.info(f"  Connected: {kg_stats['is_connected']}")

    vector_stats = engine.vector_search.get_stats()
    logger.info(f"\nVector Store:")
    logger.info(f"  Total chunks: {vector_stats['total_chunks']}")
    logger.info(f"  Narrative chunks: {vector_stats['narrative_chunks']}")
    logger.info(f"  Table chunks: {vector_stats['table_chunks']}")

    # Close
    engine.close()

    logger.info("\n" + "=" * 70)
    logger.info("Hybrid Retrieval Demo Complete")
    logger.info("=" * 70)

    logger.info("\n🔑 Key Insights:")
    logger.info("  • Vector Search: Best for facts, specific content lookup")
    logger.info("  • Graph Search: Best for concepts, relationships, prerequisites")
    logger.info("  • Hybrid Search: Combines both for comprehensive understanding")
    logger.info("  • Knowledge Gaps: Recommends next concepts based on learning progress")


if __name__ == "__main__":
    demonstrate_hybrid_retrieval()
