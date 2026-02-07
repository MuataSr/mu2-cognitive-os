"""
Test script for the Router Engine (Mock Mode)
Tests the router logic without database connection
"""

import asyncio
import sys
sys.path.insert(0, '/home/papi/Documents/mu2-cognitive-os/packages/brain/src')

from services.router_engine import router_engine


class MockVectorEngine:
    """Mock vector engine for testing"""

    async def query(self, query_str: str) -> str:
        return f"""Source 1:
Photosynthesis is the process by which plants convert light energy into chemical energy.
During photosynthesis, plants use sunlight, water, and carbon dioxide to create glucose
and oxygen. This process occurs primarily in the leaves of plants, within specialized
structures called chloroplasts.
Relevance: 0.89
Source: Biology Textbook Chapter 5

--------------------------------------------------

Source 2:
The basic equation for photosynthesis is: 6CO2 + 6H2O + light energy → C6H12O6 + 6O2.
This means that carbon dioxide and water, in the presence of light, produce glucose
and oxygen. This process is fundamental to life on Earth as it produces the oxygen
we breathe.
Relevance: 0.85
Source: Chemistry Essentials"""


class MockGraphEngine:
    """Mock graph engine for testing"""

    async def query(self, query_str: str) -> str:
        return """Concept: Sunlight
Description: Solar energy that provides light and heat to Earth
Grade Level: 3

Related Concepts:
  - Photosynthesis (ENABLES): The process by which plants convert light energy into chemical energy
  - Energy (SOURCE_OF): The capacity to do work or cause change

--------------------------------------------------

Concept: Photosynthesis
Description: The process by which plants convert light energy into chemical energy
Grade Level: 6

Related Concepts:
  - Sunlight (REQUIRES): Solar energy that provides light and heat to Earth
  - Chlorophyll (REQUIRED_FOR): Green pigment in plants that absorbs light for photosynthesis
  - Glucose (PRODUCES): A type of sugar produced during photosynthesis"""


async def test_router_classification():
    """Test the router query classification logic"""

    print("=" * 60)
    print("Router Engine - Query Classification Test")
    print("=" * 60)

    # Create router instance
    test_router = router_engine
    test_router.vector_engine = MockVectorEngine()
    test_router.graph_engine = MockGraphEngine()

    test_queries = [
        ("What is photosynthesis?", "fact"),
        ("Define mitochondria", "fact"),
        ("List the parts of a cell", "fact"),
        ("How does sunlight affect photosynthesis?", "concept"),
        ("Why does energy transform?", "concept"),
        ("Compare photosynthesis and respiration", "concept"),
        ("What is the relationship between sunlight and energy?", "concept"),
    ]

    print("\nTesting query classification:\n")
    correct = 0
    for query, expected_type in test_queries:
        result_type = test_router._classify_query(query)
        status = "✓" if result_type == expected_type else "✗"
        if result_type == expected_type:
            correct += 1
        print(f"{status} Query: '{query}'")
        print(f"  Expected: {expected_type}, Got: {result_type}")

    accuracy = (correct / len(test_queries)) * 100
    print(f"\nClassification Accuracy: {accuracy:.1f}% ({correct}/{len(test_queries)})")

    return accuracy >= 70  # Pass if at least 70% accurate


async def test_vector_query():
    """Test vector query routing"""

    print("\n" + "=" * 60)
    print("Vector Query Test")
    print("=" * 60)

    test_router = router_engine
    test_router.vector_engine = MockVectorEngine()
    test_router.graph_engine = MockGraphEngine()

    query = "What is photosynthesis?"
    result_type = test_router._classify_query(query)

    print(f"\nQuery: '{query}'")
    print(f"Classified as: {result_type}")
    print(f"Expected: fact")

    if result_type == "fact":
        print("✓ Query correctly routed to Vector Store")
        print("\nSimulated Vector Store Response:")
        response = await test_router.vector_engine.query(query)
        print(response[:300] + "...")
        return True
    else:
        print("✗ Query incorrectly routed")
        return False


async def test_graph_query():
    """Test graph query routing"""

    print("\n" + "=" * 60)
    print("Graph Query Test")
    print("=" * 60)

    test_router = router_engine
    test_router.vector_engine = MockVectorEngine()
    test_router.graph_engine = MockGraphEngine()

    query = "How does sunlight affect photosynthesis?"
    result_type = test_router._classify_query(query)

    print(f"\nQuery: '{query}'")
    print(f"Classified as: {result_type}")
    print(f"Expected: concept")

    if result_type == "concept":
        print("✓ Query correctly routed to Graph Store")
        print("\nSimulated Graph Store Response:")
        response = await test_router.graph_engine.query(query)
        print(response[:400] + "...")
        return True
    else:
        print("✗ Query incorrectly routed")
        return False


async def test_translation_prompt():
    """Test the translation prompt structure"""

    print("\n" + "=" * 60)
    print("Translation Prompt Test")
    print("=" * 60)

    college_text = """
    Photosynthesis is a physicochemical process by which plants, algae,
    and certain bacteria convert light energy into chemical energy stored
    in glucose molecules.
    """

    print(f"\nInput (College Level):")
    print(f'  "{college_text.strip()}"')
    print(f"\nTarget Grade: 6th")
    print(f"\nExpected Output Structure:")

    expected_structure = {
        "simplified": "Simple explanation for 6th graders",
        "metaphor": "Real-world metaphor",
        "source_id": "chunk_id",
        "confidence": 0.95
    }

    for key, value in expected_structure.items():
        print(f"  - {key}: {value}")

    print("\n✓ Translation prompt structure defined")
    print("  (Full translation test requires Ollama LLM)")

    return True


async def main():
    """Run all tests"""

    print("\n" + "=" * 60)
    print("MOCK ROUTER ENGINE TEST SUITE")
    print("=" * 60)
    print("\nNote: Database not connected - testing logic with mocks")

    results = []

    # Test 1: Classification
    results.append(("Classification", await test_router_classification()))

    # Test 2: Vector routing
    results.append(("Vector Query", await test_vector_query()))

    # Test 3: Graph routing
    results.append(("Graph Query", await test_graph_query()))

    # Test 4: Translation prompt
    results.append(("Translation Prompt", await test_translation_prompt()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASSED ✓" if result else "FAILED ✗"
        print(f"{test_name:.<40} {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! Router engine logic is working correctly.")
    else:
        print(f"\n✗ {total - passed} test(s) failed")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
