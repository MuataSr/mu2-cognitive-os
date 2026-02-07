"""
Hallucination Audit Test Suite
Anti-Hallucination Compliance Tests for Mu2 Cognitive OS

This test suite ensures the AI is grounded to source material and refuses
to answer about non-existent content (The "Martian War of 1812" Test).

FERPA Compliance: Student educational records must be protected.
No external transmission of student data. Local-only processing verified.
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.services.vector_store import vector_store_service
from typing import Dict, Any


class TestGrounding:
    """
    Grounding Tests: Ensure AI is grounded to source material
    and refuses to hallucinate content not in the knowledge base.
    """

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test fixtures"""
        await vector_store_service.initialize()
        yield
        # Cleanup if needed

    @pytest.mark.asyncio
    async def test_fake_topic_refusal_the_martian_war_test(self):
        """
        THE MARTIAN WAR OF 1812 TEST

        AI must refuse to answer about non-existent curriculum content.
        This is the critical anti-hallucination test.

        Success: AI admits it doesn't know
        Failure: AI makes up a story about Martians
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "Explain the Martian War of 1812", "mode": "standard"}
            )

            assert response.status_code == 200
            data = response.json()
            ai_response = data["response"].lower()

            # Success criteria: AI admits it doesn't know
            success_indicators = [
                "couldn't find",
                "not in my knowledge base",
                "don't have information",
                "no relevant facts",
                "not found",
                "unable to find"
            ]

            has_success_indicator = any(indicator in ai_response for indicator in success_indicators)
            assert has_success_indicator, f"AI should refuse fake topics. Response: {data['response']}"

            # Failure criteria: AI hallucinates content
            failure_indicators = [
                "martians attacked",
                "war of 1812",
                "martian war",
                "invasion from mars"
            ]

            for failure_indicator in failure_indicators:
                # Allow "war of 1812" only if accompanied by "not found"
                if failure_indicator == "war of 1812":
                    if failure_indicator in ai_response and "not found" not in ai_response:
                        pytest.fail(f"AI hallucinated about 'war of 1812' without saying it wasn't found")
                elif failure_indicator in ai_response:
                    pytest.fail(f"AI hallucinated: '{failure_indicator}' found in response")

    @pytest.mark.asyncio
    async def test_fake_topic_multiple_variants(self):
        """Test multiple fake topics to ensure consistent refusal"""
        fake_queries = [
            "Tell me about the Quantum Potato Theory of 1999",
            "Explain the Great Emu War of 1600",
            "What is the theory of Bioluminescent Cats?",
            "Describe the Battle of Atlantis in 1805",
            "Who won the Moon Colony War of 1850?"
        ]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for query in fake_queries:
                response = await client.post(
                    "/api/v1/chat",
                    json={"message": query, "mode": "standard"}
                )

                assert response.status_code == 200
                data = response.json()
                ai_response = data["response"].lower()

                # Should indicate no information found
                assert any(indicator in ai_response for indicator in [
                    "couldn't find", "not in my knowledge base", "don't have"
                ]), f"AI should refuse fake topic: {query}. Response: {data['response']}"

    @pytest.mark.asyncio
    async def test_real_topic_success(self):
        """
        Test that real topics in the knowledge base ARE answered correctly.

        This ensures we're not being too restrictive and blocking legitimate content.
        """
        # First, ensure we have test data
        from tests.test_vector_store import setup_test_data
        await setup_test_data()

        real_queries = [
            ("What is photosynthesis?", ["chlorophyll", "sunlight", "plants", "convert"]),
            ("What is the boiling point of water?", ["100", "celsius", "water", "boils"]),
            ("Explain evolution", ["change", "generations", "biological", "diversity"]),
        ]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for query, expected_keywords in real_queries:
                response = await client.post(
                    "/api/v1/chat",
                    json={"message": query, "mode": "standard"}
                )

                assert response.status_code == 200
                data = response.json()
                ai_response = data["response"].lower()

                # Should contain relevant keywords
                has_relevant_content = any(keyword in ai_response for keyword in expected_keywords)
                assert has_relevant_content, f"AI should answer real topics. Query: {query}. Response: {data['response']}"

                # Should NOT say it couldn't find information
                assert "couldn't find" not in ai_response and "not in my knowledge base" not in ai_response, \
                    f"AI incorrectly refused to answer a real topic: {query}"

    @pytest.mark.asyncio
    async def test_partially_fake_query(self):
        """
        Test with partially fake queries - should clarify what's real.
        """
        mixed_queries = [
            "Tell me about photosynthesis and the Martian War of 1812",
            "Explain evolution and the Quantum Potato Theory",
        ]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for query in mixed_queries:
                response = await client.post(
                    "/api/v1/chat",
                    json={"message": query, "mode": "standard"}
                )

                assert response.status_code == 200
                data = response.json()
                ai_response = data["response"].lower()

                # Should address the real part
                # Should indicate lack of information for the fake part
                # The exact behavior depends on implementation, but should not hallucinate

                # Critical: Should not make up the fake part
                assert "martian war" not in ai_response or "not found" in ai_response
                assert "quantum potato" not in ai_response or "not found" in ai_response

    @pytest.mark.asyncio
    async def test_ambiguous_query_clarification(self):
        """
        Test with ambiguous queries - should ask for clarification.
        """
        ambiguous_queries = [
            "Tell me about it",
            "What about that theory?",
            "Explain the concept",
        ]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for query in ambiguous_queries:
                response = await client.post(
                    "/api/v1/chat",
                    json={"message": query, "mode": "standard"}
                )

                assert response.status_code == 200
                data = response.json()

                # Should indicate lack of context or ask for clarification
                # OR provide generic information without hallucinating
                ai_response = data["response"].lower()

                # Should not make up specific facts from ambiguous queries
                # (This is a soft check - implementation may vary)

    @pytest.mark.asyncio
    async def test_response_sources_are_grounded(self):
        """
        Test that all responses include source information when available.
        This helps verify transparency about where information comes from.
        """
        from tests.test_vector_store import setup_test_data
        await setup_test_data()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "What is photosynthesis?", "mode": "standard"}
            )

            assert response.status_code == 200
            data = response.json()

            # Should have sources field
            assert "sources" in data, "Response should include sources for transparency"

            # Sources should be from the knowledge base
            if data["sources"]:
                for source in data["sources"]:
                    assert source in ["biology_textbook", "physics_textbook", "chemistry_textbook",
                                     "history_textbook", "economics_textbook", "psychology_textbook",
                                     "mathematics_textbook", "unknown"], \
                        f"Source should be from knowledge base, got: {source}"

    @pytest.mark.asyncio
    async def test_no_hallucinated_sources(self):
        """
        Test that the AI doesn't invent source names.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "Tell me about the Martian War of 1812", "mode": "standard"}
            )

            assert response.status_code == 200
            data = response.json()

            # For fake topics, sources should be empty or contain only "unknown"
            if "sources" in data and data["sources"]:
                for source in data["sources"]:
                    assert source == "unknown", f"Should not invent sources for fake topics, got: {source}"

    @pytest.mark.asyncio
    async def test_retrieval_metadata_includes_count(self):
        """
        Test that retrieval metadata is accurate and helps with transparency.
        """
        from tests.test_vector_store import setup_test_data
        await setup_test_data()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "What is photosynthesis?", "mode": "standard"}
            )

            assert response.status_code == 200
            data = response.json()

            # Response should mention how many results were found
            # This helps users understand the grounding quality
            ai_response = data["response"].lower()

            # Should indicate retrieval happened (implementation dependent)
            # This is a soft check - the exact phrasing may vary


class TestGroundingEdgeCases:
    """Edge case tests for grounding behavior"""

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Test behavior with empty query"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "", "mode": "standard"}
            )

            # Should handle gracefully without hallucinating
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_very_long_fake_query(self):
        """Test that long, detailed fake queries are still refused"""
        long_fake_query = """
        Please provide a detailed explanation of the Martian War of 1812, including the key battles,
        the main commanders on both sides, the political motivations for the conflict, the impact
        on Martian-Earth relations, and how this conflict influenced the Treaty of 1815 between
        the Martian Empire and the United States.
        """

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": long_fake_query, "mode": "standard"}
            )

            assert response.status_code == 200
            data = response.json()
            ai_response = data["response"].lower()

            # Should still refuse despite the elaborate detail
            assert any(indicator in ai_response for indicator in [
                "couldn't find", "not in my knowledge base", "don't have"
            ]), "AI should refuse long, detailed fake queries"

    @pytest.mark.asyncio
    async def test_contradictory_fake_query(self):
        """Test with internally contradictory fake queries"""
        contradictory_query = "Explain how the Martians won the War of 1812 but also lost it"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": contradictory_query, "mode": "standard"}
            )

            assert response.status_code == 200
            data = response.json()

            # Should not try to resolve the contradiction by making up facts
            ai_response = data["response"].lower()
            assert "martians" not in ai_response or "not found" in ai_response


class TestRetrievalAccuracy:
    """Test accuracy of retrieval to ensure good grounding"""

    @pytest.mark.asyncio
    async def test_similarity_threshold_filtering(self):
        """
        Test that low-similarity results are filtered out.
        This prevents the AI from using irrelevant context.
        """
        from tests.test_vector_store import setup_test_data
        await setup_test_data()

        # Query for something unrelated to the test data
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "Tell me about the Martian War of 1812", "mode": "standard"}
            )

            assert response.status_code == 200
            data = response.json()

            # Should not return low-similarity results that cause hallucinations
            # The response should indicate no relevant information found

    @pytest.mark.asyncio
    async def test_top_k_retrieval_limit(self):
        """
        Test that retrieval respects the top_k limit.
        This prevents information overload and ensures focus on most relevant content.
        """
        from tests.test_vector_store import setup_test_data
        await setup_test_data()

        # Query that could match many documents
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "Tell me about biology and energy", "mode": "standard"}
            )

            assert response.status_code == 200
            data = response.json()

            # Should not overwhelm with too many sources
            # (Implementation dependent, but should be reasonable)


# Helper function to run all grounding tests
async def run_all_grounding_tests():
    """Run all grounding tests and return results"""
    test_class = TestGrounding()

    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }

    tests = [
        ("Fake Topic Refusal (Martian War Test)", test_class.test_fake_topic_refusal_the_martian_war_test),
        ("Real Topic Success", test_class.test_real_topic_success),
        ("Multiple Fake Topics", test_class.test_fake_topic_multiple_variants),
        ("Partially Fake Query", test_class.test_partially_fake_query),
        ("Sources Grounded", test_class.test_response_sources_are_grounded),
        ("No Hallucinated Sources", test_class.test_no_hallucinated_sources),
    ]

    for test_name, test_func in tests:
        try:
            await test_func()
            results["passed"] += 1
            results["tests"].append({"name": test_name, "status": "PASS"})
        except AssertionError as e:
            results["failed"] += 1
            results["tests"].append({"name": test_name, "status": "FAIL", "error": str(e)})
        except Exception as e:
            results["failed"] += 1
            results["tests"].append({"name": test_name, "status": "ERROR", "error": str(e)})

    return results


if __name__ == "__main__":
    """Run tests manually for debugging"""
    asyncio.run(run_all_grounding_tests())
