#!/usr/bin/env python3
"""
Test Complete Hybrid Retrieval System
======================================

Tests the full Mu2 Cognitive OS retrieval capabilities:
1. Vector Search (pgvector) - For factual content
2. Knowledge Graph - For concept relationships and prerequisites
3. Hybrid Retrieval - Combines both for comprehensive answers

This test uses the newly processed data from all 21 chapters.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph.morning_circle import morning_circle_graph
from src.services.openstax_embedding_service import OllamaEmbeddingService
from src.services.graph_retrieval_service import GraphRetrievalService
from src.core.state import MorningCircleState

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test queries covering different retrieval types
TEST_QUERIES = [
    {
        "type": "fact",
        "query": "What are the three branches of government?",
        "description": "Direct factual question - should use vector search"
    },
    {
        "type": "concept",
        "query": "Explain the concept of federalism",
        "description": "Concept explanation - should use knowledge graph"
    },
    {
        "type": "hybrid",
        "query": "How does federalism relate to the separation of powers?",
        "description": "Concept relationships - should use hybrid retrieval"
    },
    {
        "type": "learning_path",
        "query": "What should I learn before understanding the electoral college?",
        "description": "Prerequisites - should use knowledge graph"
    },
    {
        "type": "comparison",
        "query": "Compare civil liberties and civil rights",
        "description": "Comparison - should use hybrid retrieval"
    },
    {
        "type": "fact",
        "query": "What is the Articles of Confederation?",
        "description": "Historical fact - should use vector search"
    },
    {
        "type": "complex",
        "query": "How does the First Amendment protect freedom of speech while allowing for some restrictions?",
        "description": "Complex multi-part - should use hybrid retrieval"
    },
]


async def test_single_query(graph_app, query: str, query_type: str, description: str):
    """Test a single query through the hybrid system"""
    print("\n" + "=" * 70)
    print(f"QUERY: {query}")
    print(f"Type: {query_type}")
    print(f"Description: {description}")
    print("=" * 70)

    # Create initial state
    initial_state: MorningCircleState = {
        "mode": "standard",  # Required field
        "user_id": "test_user",
        "message": query,
        "original_message": None,
        "anonymized_message": None,
        "sentiment": "neutral",
        "conversation_history": [],
        "retrieval_type": "auto",  # Let the router decide
        "sources": [],
        "retrieved_context": {},
        "graph_concepts": [],
        "graph_relationships": [],
        "learning_path": None,
        "prerequisites": None,
        "suggested_mode": "standard",
        "urgency": "none"
    }

    try:
        # Run through the graph
        print("\n🔄 Processing through LangGraph...")
        result_state = await graph_app.ainvoke(initial_state)

        # Display results
        print("\n📊 RETRIEVAL RESULTS:")
        print("-" * 70)

        # Show routing decision
        retrieval_type = result_state.get("retrieval_type", "unknown")
        print(f"Routing Decision: {retrieval_type.upper()}")

        # Show sources
        sources = result_state.get("sources", [])
        if sources:
            print(f"\n📚 Sources Found: {len(sources)}")
            for i, source in enumerate(sources[:5], 1):
                print(f"  {i}. {source}")
            if len(sources) > 5:
                print(f"  ... and {len(sources) - 5} more")

        # Show knowledge graph results
        graph_concepts = result_state.get("graph_concepts", [])
        if graph_concepts:
            print(f"\n🕸️  Knowledge Graph Concepts: {len(graph_concepts)}")
            for i, concept in enumerate(graph_concepts[:5], 1):
                if isinstance(concept, dict):
                    name = concept.get("name", "Unknown")
                    relationship = concept.get("relationship", "related")
                    print(f"  {i}. {name} ({relationship})")
                else:
                    print(f"  {i}. {concept}")
            if len(graph_concepts) > 5:
                print(f"  ... and {len(graph_concepts) - 5} more")

        # Show prerequisites if available
        prerequisites = result_state.get("prerequisites")
        if prerequisites:
            print(f"\n📖 Prerequisites: {len(prerequisites)}")
            for prereq in prerequisites[:5]:
                print(f"  • {prereq}")

        # Show learning path if available
        learning_path = result_state.get("learning_path")
        if learning_path:
            print(f"\n🎯 Learning Path: {len(learning_path)} steps")
            for i, step in enumerate(learning_path[:5], 1):
                print(f"  {i}. {step}")

        # Show suggested mode
        suggested_mode = result_state.get("suggested_mode")
        if suggested_mode:
            mode_icons = {"standard": "📖", "focus": "🎯", "high_contrast_focus": "⚡"}
            icon = mode_icons.get(suggested_mode, "📱")
            print(f"\n{icon} Suggested Mode: {suggested_mode}")

        # Show retrieved context summary
        retrieved_context = result_state.get("retrieved_context", {})
        if retrieved_context:
            chunks = retrieved_context.get("chunks", [])
            if chunks:
                print(f"\n📄 Context Chunks: {len(chunks)}")
                total_words = sum(c.get("word_count", 0) for c in chunks)
                print(f"  Total context: {total_words} words")

        print("\n" + "=" * 70)
        print("✅ Query processed successfully")

        return {
            "query": query,
            "type": query_type,
            "routing": retrieval_type,
            "sources_count": len(sources),
            "concepts_count": len(graph_concepts),
            "success": True
        }

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "query": query,
            "type": query_type,
            "success": False,
            "error": str(e)
        }


async def test_vector_only():
    """Test pure vector search"""
    print("\n" + "=" * 70)
    print("TEST 1: Pure Vector Search (pgvector)")
    print("=" * 70)

    from src.services.sqlite_vector_store import SQLiteVectorStore
    from src.core.config import OPENSTAX_CHUNKS_DIR

    vector_store = SQLiteVectorStore(str(OPENSTAX_CHUNKS_DIR / "chunks.db"))

    # Test query
    query = "What are the powers of the presidency?"
    print(f"\nQuery: {query}")

    # Get embedding for query
    embedding_service = OllamaEmbeddingService()
    test_chunks = [type('Chunk', (), {
        'chunk_id': 'test',
        'title': 'test',
        'content': query
    })()]
    result = await embedding_service.embed_chunks(test_chunks, show_progress=False)
    query_embedding = result.embedded_chunks[0].embedding

    # Search
    search_results = vector_store.search_similar(query_embedding, limit=5)

    print(f"\n📚 Vector Search Results: {len(search_results)} chunks found")
    for i, result in enumerate(search_results, 1):
        print(f"\n  {i}. {result['title']}")
        print(f"     Similarity: {result['similarity']:.4f}")
        print(f"     Concepts: {', '.join(result.get('key_concepts', [])[:3])}")


async def test_graph_only():
    """Test pure knowledge graph retrieval"""
    print("\n" + "=" * 70)
    print("TEST 2: Pure Knowledge Graph Retrieval")
    print("=" * 70)

    from src.services.graph_retrieval_service import GraphRetrievalService

    graph_service = GraphRetrievalService()
    await graph_service.ensure_initialized()

    # Test concept search
    query = "federalism"
    print(f"\nQuery: {query}")

    concepts = await graph_service.search_concepts(query, limit=5)
    print(f"\n🕸️  Concepts Found: {len(concepts)}")
    for i, concept in enumerate(concepts, 1):
        print(f"\n  {i}. {concept['name']}")
        print(f"     Chapter: {concept.get('chapter_id', 'Unknown')}")

        # Get related concepts
        related = await graph_service.get_related_concepts(concept['name'], max_distance=2)
        if related:
            related_names = [r['name'] for r in related[:3]]
            print(f"     Related: {', '.join(related_names)}")

    # Test prerequisites
    print(f"\n\n📖 Prerequisites for 'federalism':")
    prereqs = await graph_service.get_prerequisites("federalism", depth=2)
    if prereqs:
        for prereq in prereqs[:5]:
            print(f"  • {prereq['name']}")
    else:
        print("  None found")


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("Mu2 Cognitive OS - Complete Hybrid Retrieval Test")
    print("=" * 70)
    print("\n🧪 Testing with data from all 21 chapters of American Government")
    print("   - 881 chunks with vector embeddings")
    print("   - 1,802 concepts in knowledge graph")
    print("   - 30,177 relationships between concepts")

    # Initialize the graph app
    print("\n⏳ Initializing LangGraph application...")
    # The graph is already compiled as morning_circle_graph
    from src.graph.morning_circle import morning_circle_graph
    graph_app = morning_circle_graph

    # Initialize graph service
    graph_service = GraphRetrievalService()
    await graph_service.ensure_initialized()
    print("✅ Initialization complete")

    # Run tests
    results = []
    for test_case in TEST_QUERIES:
        result = await test_single_query(
            graph_app,
            test_case["query"],
            test_case["type"],
            test_case["description"]
        )
        results.append(result)

    # Summary
    print("\n\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)

    print(f"\n✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {total - successful}/{total}")

    # Breakdown by routing type
    routing_counts = {}
    for result in results:
        if result.get("success"):
            routing = result.get("routing", "unknown")
            routing_counts[routing] = routing_counts.get(routing, 0) + 1

    print("\n📈 Routing Distribution:")
    for routing, count in sorted(routing_counts.items()):
        percentage = (count / successful) * 100 if successful > 0 else 0
        bar = "█" * int(percentage / 5)
        print(f"  {routing:15} {count:2} ({percentage:5.1f}%) {bar}")

    print("\n" + "=" * 70)
    print("🎉 Testing complete!")
    print("=" * 70)

    return results


if __name__ == "__main__":
    asyncio.run(main())
