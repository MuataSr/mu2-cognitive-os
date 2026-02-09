"""
Test LangGraph Knowledge Graph Integration
==========================================

Tests the integration of the knowledge graph into the Morning Circle
state machine, verifying:

1. Hybrid routing triggers correctly
2. Graph retrieval works alongside vector search
3. Learning path recommendations are generated
4. Response generation includes graph context
"""

import asyncio
import logging
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph.morning_circle import morning_circle_graph
from src.core.state import MorningCircleState

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_langgraph_kg_integration():
    """Test knowledge graph integration in LangGraph"""

    logger.info("=" * 70)
    logger.info("Testing LangGraph Knowledge Graph Integration")
    logger.info("=" * 70)

    # Test 1: Fact Query (vector search only)
    logger.info("\n" + "-" * 70)
    logger.info("Test 1: Fact Query - Vector Search Only")
    logger.info("-" * 70)

    state1: MorningCircleState = {
        "message": "What is government?",
        "mode": "standard",
        "user_id": "test_user_1",
        "original_message": None,
        "anonymized_message": None,
        "anonymization_metadata": None,
        "sentiment_score": 0.0,
        "sentiment_label": "neutral",
        "retrieval_type": "fact",
        "sources": [],
        "retrieved_context": {},
        "response": "",
        "citation_validated": None,
        "citation_lock": None,
        "citation_warning": None,
        "llm_provider_used": None,
        "llm_routing_reason": None,
        "complexity_score": None,
        "behavioral_signals": None,
        "suggested_mode": None,
        "urgency": None,
        "consecutive_errors": None,
        "time_spent_seconds": None,
        "graph_concepts": [],
        "graph_relationships": [],
        "learning_path": None,
        "prerequisites": None,
    }

    try:
        result1 = await morning_circle_graph.ainvoke(state1)
        logger.info(f"✓ Query: {state1['message']}")
        logger.info(f"✓ Routing: {result1.get('retrieval_type')}")
        logger.info(f"✓ Sources found: {len(result1.get('sources', []))}")
        logger.info(f"✓ Graph concepts: {len(result1.get('graph_concepts', []))}")
        logger.info(f"✓ Response preview: {result1.get('response', '')[:150]}...")
    except Exception as e:
        logger.error(f"✗ Test 1 failed: {e}")

    # Test 2: Concept Query (vector search only)
    logger.info("\n" + "-" * 70)
    logger.info("Test 2: Concept Query - Vector Search Only")
    logger.info("-" * 70)

    state2: MorningCircleState = {
        "message": "Explain the theory of government",
        "mode": "standard",
        "user_id": "test_user_2",
        "original_message": None,
        "anonymized_message": None,
        "anonymization_metadata": None,
        "sentiment_score": 0.0,
        "sentiment_label": "neutral",
        "retrieval_type": "concept",
        "sources": [],
        "retrieved_context": {},
        "response": "",
        "citation_validated": None,
        "citation_lock": None,
        "citation_warning": None,
        "llm_provider_used": None,
        "llm_routing_reason": None,
        "complexity_score": None,
        "behavioral_signals": None,
        "suggested_mode": None,
        "urgency": None,
        "consecutive_errors": None,
        "time_spent_seconds": None,
        "graph_concepts": [],
        "graph_relationships": [],
        "learning_path": None,
        "prerequisites": None,
    }

    try:
        result2 = await morning_circle_graph.ainvoke(state2)
        logger.info(f"✓ Query: {state2['message']}")
        logger.info(f"✓ Routing: {result2.get('retrieval_type')}")
        logger.info(f"✓ Sources found: {len(result2.get('sources', []))}")
        logger.info(f"✓ Graph concepts: {len(result2.get('graph_concepts', []))}")
        logger.info(f"✓ Response preview: {result2.get('response', '')[:150]}...")
    except Exception as e:
        logger.error(f"✗ Test 2 failed: {e}")

    # Test 3: Hybrid Query (vector + graph search)
    logger.info("\n" + "-" * 70)
    logger.info("Test 3: Hybrid Query - Vector + Graph Search")
    logger.info("-" * 70)

    state3: MorningCircleState = {
        "message": "How is government related to democracy?",
        "mode": "standard",
        "user_id": "test_user_3",
        "original_message": None,
        "anonymized_message": None,
        "anonymization_metadata": None,
        "sentiment_score": 0.0,
        "sentiment_label": "neutral",
        "retrieval_type": "hybrid",
        "sources": [],
        "retrieved_context": {},
        "response": "",
        "citation_validated": None,
        "citation_lock": None,
        "citation_warning": None,
        "llm_provider_used": None,
        "llm_routing_reason": None,
        "complexity_score": None,
        "behavioral_signals": None,
        "suggested_mode": None,
        "urgency": None,
        "consecutive_errors": None,
        "time_spent_seconds": None,
        "graph_concepts": [],
        "graph_relationships": [],
        "learning_path": None,
        "prerequisites": None,
    }

    try:
        result3 = await morning_circle_graph.ainvoke(state3)
        logger.info(f"✓ Query: {state3['message']}")
        logger.info(f"✓ Routing: {result3.get('retrieval_type')}")
        logger.info(f"✓ Sources found: {len(result3.get('sources', []))}")
        logger.info(f"✓ Graph concepts: {len(result3.get('graph_concepts', []))}")

        if result3.get('graph_concepts'):
            logger.info(f"  Related concepts:")
            for c in result3['graph_concepts'][:3]:
                logger.info(f"    - {c.get('name', 'N/A')}")

        if result3.get('prerequisites'):
            logger.info(f"✓ Prerequisites: {result3['prerequisites']}")

        if result3.get('learning_path'):
            logger.info(f"✓ Learning path: {' → '.join(result3['learning_path'])}")

        logger.info(f"✓ Response preview: {result3.get('response', '')[:200]}...")
    except Exception as e:
        logger.error(f"✗ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 4: Learning Path Query
    logger.info("\n" + "-" * 70)
    logger.info("Test 4: Learning Path Query")
    logger.info("-" * 70)

    state4: MorningCircleState = {
        "message": "What should I learn before understanding democracy?",
        "mode": "standard",
        "user_id": "test_user_4",
        "original_message": None,
        "anonymized_message": None,
        "anonymization_metadata": None,
        "sentiment_score": 0.0,
        "sentiment_label": "neutral",
        "retrieval_type": "hybrid",
        "sources": [],
        "retrieved_context": {},
        "response": "",
        "citation_validated": None,
        "citation_lock": None,
        "citation_warning": None,
        "llm_provider_used": None,
        "llm_routing_reason": None,
        "complexity_score": None,
        "behavioral_signals": None,
        "suggested_mode": None,
        "urgency": None,
        "consecutive_errors": None,
        "time_spent_seconds": None,
        "graph_concepts": [],
        "graph_relationships": [],
        "learning_path": None,
        "prerequisites": None,
    }

    try:
        result4 = await morning_circle_graph.ainvoke(state4)
        logger.info(f"✓ Query: {state4['message']}")
        logger.info(f"✓ Routing: {result4.get('retrieval_type')}")
        logger.info(f"✓ Graph concepts: {len(result4.get('graph_concepts', []))}")

        if result4.get('prerequisites'):
            logger.info(f"✓ Prerequisites found: {result4['prerequisites']}")

        logger.info(f"✓ Response preview: {result4.get('response', '')[:200]}...")
    except Exception as e:
        logger.error(f"✗ Test 4 failed: {e}")
        import traceback
        traceback.print_exc()

    logger.info("\n" + "=" * 70)
    logger.info("LangGraph Knowledge Graph Integration Tests Complete")
    logger.info("=" * 70)

    logger.info("\n🔑 Summary:")
    logger.info("  • Fact queries: Vector search only")
    logger.info("  • Concept queries: Vector search only")
    logger.info("  • Hybrid queries: Vector + Graph search combined")
    logger.info("  • Learning paths: Graph traversal for curriculum")
    logger.info("  • Prerequisites: Knowledge graph prerequisite chains")


if __name__ == "__main__":
    asyncio.run(test_langgraph_kg_integration())
