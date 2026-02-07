"""
Test script for vector store integration
Populates database with sample data and tests retrieval
"""

import asyncio
from src.services.vector_store import vector_store_service


async def setup_test_data():
    """Populate the vector store with test knowledge chunks"""

    print("Setting up test data...")

    # Fact chunks - specific, concrete information
    facts = [
        {
            "content": "Photosynthesis is the process by which plants convert sunlight, water, and carbon dioxide into glucose and oxygen. This process occurs in the chloroplasts of plant cells.",
            "chunk_type": "fact",
            "source": "biology_textbook",
            "metadata": {"topic": "biology", "subtopic": "photosynthesis"},
        },
        {
            "content": "The mitochondria is the powerhouse of the cell, producing ATP through cellular respiration. It has its own DNA and is believed to have evolved from ancient bacteria.",
            "chunk_type": "fact",
            "source": "biology_textbook",
            "metadata": {"topic": "biology", "subtopic": "cell_biology"},
        },
        {
            "content": "Newton's First Law of Motion states that an object at rest stays at rest and an object in motion stays in motion with the same speed and in the same direction unless acted upon by an unbalanced force.",
            "chunk_type": "fact",
            "source": "physics_textbook",
            "metadata": {"topic": "physics", "subtopic": "mechanics"},
        },
        {
            "content": "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at standard atmospheric pressure. The boiling point decreases at higher altitudes due to lower atmospheric pressure.",
            "chunk_type": "fact",
            "source": "chemistry_textbook",
            "metadata": {"topic": "chemistry", "subtopic": "matter"},
        },
        {
            "content": "The French Revolution began in 1789 and lasted until 1799. It led to the rise of Napoleon Bonaparte and the end of the monarchy in France.",
            "chunk_type": "fact",
            "source": "history_textbook",
            "metadata": {"topic": "history", "subtopic": "european_history"},
        },
    ]

    # Concept chunks - abstract, theoretical explanations
    concepts = [
        {
            "content": "Evolution is the process of change in all forms of life over generations. Evolutionary processes give rise to diversity at every level of biological organization, including species, individual organisms, and molecules.",
            "chunk_type": "concept",
            "source": "biology_textbook",
            "metadata": {"topic": "biology", "subtopic": "evolution"},
        },
        {
            "content": "Entropy is a thermodynamic quantity representing the unavailability of a system's thermal energy for conversion into mechanical work. It is also a measure of the number of specific ways in which a thermodynamic system may be arranged.",
            "chunk_type": "concept",
            "source": "physics_textbook",
            "metadata": {"topic": "physics", "subtopic": "thermodynamics"},
        },
        {
            "content": "Supply and demand is an economic model of price determination in a market. It postulates that, holding all else equal, in a competitive market, the unit price for a particular good will vary until it settles at a point where the quantity demanded equals the quantity supplied.",
            "chunk_type": "concept",
            "source": "economics_textbook",
            "metadata": {"topic": "economics", "subtopic": "microeconomics"},
        },
        {
            "content": "Cognitive dissonance is the mental discomfort experienced by a person who holds two or more contradictory beliefs, ideas, or values at the same time, or is confronted by new information that conflicts with existing beliefs, ideas, or values.",
            "chunk_type": "concept",
            "source": "psychology_textbook",
            "metadata": {"topic": "psychology", "subtopic": "social_psychology"},
        },
        {
            "content": "The concept of infinity refers to something that is without any limit or end. In mathematics, infinity is often treated as a number but it's actually a concept that describes something that grows without bound.",
            "chunk_type": "concept",
            "source": "mathematics_textbook",
            "metadata": {"topic": "mathematics", "subtopic": "calculus"},
        },
    ]

    # Add facts to vector store
    print(f"\nAdding {len(facts)} fact chunks...")
    for i, fact in enumerate(facts):
        node_id = await vector_store_service.add_knowledge_chunk(
            content=fact["content"],
            chunk_type=fact["chunk_type"],
            source=fact["source"],
            metadata=fact["metadata"],
        )
        print(f"  [{i+1}/{len(facts)}] Added fact: {fact['metadata']['subtopic']} (ID: {node_id})")

    # Add concepts to vector store
    print(f"\nAdding {len(concepts)} concept chunks...")
    for i, concept in enumerate(concepts):
        node_id = await vector_store_service.add_knowledge_chunk(
            content=concept["content"],
            chunk_type=concept["chunk_type"],
            source=concept["source"],
            metadata=concept["metadata"],
        )
        print(f"  [{i+1}/{len(concepts)}] Added concept: {concept['metadata']['subtopic']} (ID: {node_id})")

    print("\nTest data setup complete!")


async def test_fact_retrieval():
    """Test fact retrieval with sample queries"""

    print("\n" + "=" * 80)
    print("TESTING FACT RETRIEVAL")
    print("=" * 80)

    fact_queries = [
        "What is photosynthesis?",
        "What is the boiling point of water?",
        "What is Newton's First Law?",
    ]

    for query in fact_queries:
        print(f"\nQuery: {query}")
        results = await vector_store_service.retrieve_facts(query, top_k=3)

        if results:
            print(f"Found {len(results)} relevant fact(s):")
            for i, result in enumerate(results, 1):
                print(f"\n  [{i}] Score: {result['score']:.4f}")
                print(f"      Content: {result['content'][:150]}...")
                print(f"      Source: {result['metadata'].get('source', 'unknown')}")
        else:
            print("  No relevant facts found.")


async def test_concept_retrieval():
    """Test concept retrieval with sample queries"""

    print("\n" + "=" * 80)
    print("TESTING CONCEPT RETRIEVAL")
    print("=" * 80)

    concept_queries = [
        "Explain evolution",
        "What is entropy?",
        "How does supply and demand work?",
    ]

    for query in concept_queries:
        print(f"\nQuery: {query}")
        results = await vector_store_service.retrieve_concepts(query, top_k=3)

        if results:
            print(f"Found {len(results)} relevant concept(s):")
            for i, result in enumerate(results, 1):
                print(f"\n  [{i}] Score: {result['score']:.4f}")
                print(f"      Content: {result['content'][:150]}...")
                print(f"      Source: {result['metadata'].get('source', 'unknown')}")
        else:
            print("  No relevant concepts found.")


async def test_hybrid_retrieval():
    """Test hybrid retrieval without type filtering"""

    print("\n" + "=" * 80)
    print("TESTING HYBRID RETRIEVAL")
    print("=" * 80)

    query = "Tell me about cells and energy"
    print(f"\nQuery: {query}")
    results = await vector_store_service.retrieve_hybrid(query, top_k=5)

    if results:
        print(f"Found {len(results)} relevant result(s):")
        for i, result in enumerate(results, 1):
            chunk_type = result['metadata'].get('chunk_type', 'unknown')
            print(f"\n  [{i}] Score: {result['score']:.4f} | Type: {chunk_type}")
            print(f"      Content: {result['content'][:150]}...")
    else:
        print("  No relevant results found.")


async def test_embedding():
    """Test embedding generation"""

    print("\n" + "=" * 80)
    print("TESTING EMBEDDING GENERATION")
    print("=" * 80)

    test_text = "This is a test sentence for embedding generation."
    print(f"\nText: {test_text}")

    embedding = await vector_store_service.get_embedding(test_text)
    print(f"Embedding dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")


async def main():
    """Main test function"""

    print("=" * 80)
    print("Mu2 Cognitive OS - Vector Store Integration Test")
    print("=" * 80)

    # Initialize vector store
    print("\nInitializing vector store...")
    await vector_store_service.initialize()

    # Health check
    print("\nHealth check:")
    health = await vector_store_service.health_check()
    for key, value in health.items():
        print(f"  {key}: {value}")

    # Setup test data
    await setup_test_data()

    # Run tests
    await test_fact_retrieval()
    await test_concept_retrieval()
    await test_hybrid_retrieval()
    await test_embedding()

    print("\n" + "=" * 80)
    print("All tests complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
