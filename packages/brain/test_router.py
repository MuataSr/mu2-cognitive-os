"""
Test script for the Router Engine
Tests vector and graph queries
"""

import asyncio
import sys
sys.path.insert(0, '/home/papi/Documents/mu2-cognitive-os/packages/brain/src')

from services.router_engine import router_engine


async def test_router():
    """Test the router engine with sample queries"""

    print("=" * 60)
    print("Router Engine Test")
    print("=" * 60)

    # Initialize the router
    print("\n1. Initializing router engine...")
    await router_engine.initialize()
    print("   ✓ Router initialized")

    # Check health
    print("\n2. Checking health...")
    health = await router_engine.health_check()
    print(f"   Status: {health['status']}")
    print(f"   LLM Model: {health.get('llm_model', 'N/A')}")
    print(f"   Vector Engine: {health['vector_engine_configured']}")
    print(f"   Graph Engine: {health['graph_engine_configured']}")

    # Test 1: Vector query (factual)
    print("\n3. Testing VECTOR query (factual):")
    print("   Query: 'What is photosynthesis?'")
    vector_result = await router_engine.query(
        query_str="What is photosynthesis?",
        retrieve_mode="vector"
    )
    print(f"   Engine used: {vector_result['engine_used']}")
    print(f"   Query type: {vector_result['query_type']}")
    print(f"   Result preview: {vector_result['result'][:300]}...")

    # Test 2: Graph query (conceptual)
    print("\n4. Testing GRAPH query (conceptual):")
    print("   Query: 'How does sunlight affect photosynthesis?'")
    graph_result = await router_engine.query(
        query_str="How does sunlight affect photosynthesis?",
        retrieve_mode="graph"
    )
    print(f"   Engine used: {graph_result['engine_used']}")
    print(f"   Query type: {graph_result['query_type']}")
    print(f"   Result preview: {graph_result['result'][:300]}...")

    # Test 3: Auto router
    print("\n5. Testing AUTO router:")
    print("   Query: 'Define energy'")
    auto_result = await router_engine.query(
        query_str="Define energy",
        retrieve_mode="auto"
    )
    print(f"   Engine used: {auto_result['engine_used']}")
    print(f"   Query type: {auto_result['query_type']}")
    print(f"   Result preview: {auto_result['result'][:300]}...")

    # Test 4: Translation
    print("\n6. Testing translation (The Translator):")
    college_text = """
    Photosynthesis is a physicochemical process by which plants, algae,
    and certain bacteria convert light energy into chemical energy stored
    in glucose molecules. This process occurs in chloroplasts and involves
    the pigment chlorophyll absorbing photons to drive electron transport chains.
    """
    print(f"   Input: {college_text[:100]}...")
    print("   Target grade: 6th")

    translation = await router_engine.translate_to_grade_level(
        college_text=college_text.strip(),
        grade_level=6,
        source_id="bio_textbook_ch3"
    )
    print(f"   ✓ Translation complete")
    print(f"   Simplified: {translation['simplified'][:200]}...")
    print(f"   Metaphor: {translation['metaphor']}")
    print(f"   Source ID: {translation['source_id']}")
    print(f"   Confidence: {translation['confidence']}")

    # Test 5: Graph relations
    print("\n7. Testing graph relations:")
    relations = await router_engine.get_graph_relations("photosynthesis")
    print(f"   Found {len(relations)} relations for 'photosynthesis'")
    if relations:
        for rel in relations[:3]:
            print(f"   - {rel['target']} ({rel['relationship']})")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_router())
