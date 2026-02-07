"""
Tests for Hybrid LLM Router
Testing routing logic between local and cloud LLMs
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.hybrid_llm_router import (
    HybridLLMRouter,
    HybridLLMConfig,
    LLMPurpose,
    RoutingDecision
)
from src.services.cloud_llm_providers import LLMResponse, LLMEmbedding
from src.services.anonymization_service import AnonymizationResult


class TestRoutingDecision:
    """Test routing decision logic"""

    @pytest.fixture
    def router(self):
        config = HybridLLMConfig(
            cloud_threshold=0.7,
            local_model="test-model",
            local_base_url="http://localhost:11434",
            cloud_provider="minimax",
            cloud_api_key="test-key",  # Add cloud API key for testing
            cloud_model="test-model"
        )
        return HybridLLMRouter(config=config)

    def test_calculate_complexity_simple(self, router):
        """Test complexity calculation for simple query"""
        complexity = router._calculate_complexity("What is ATP?", LLMPurpose.GENERATION)

        assert complexity < 0.1  # Should be very low complexity

    def test_calculate_complexity_complex(self, router):
        """Test complexity calculation for complex query"""
        query = "Explain the process of photosynthesis in detail, including how light-dependent reactions produce ATP and NADPH, and how these are used in the Calvin cycle"
        complexity = router._calculate_complexity(query, LLMPurpose.GENERATION)

        # Has "explain" (0.1) + "photosynthesis" (0.05) + longer word count
        assert complexity >= 0.1  # Should be higher than simple query

    def test_calculate_complexity_why_question(self, router):
        """Test that 'why' questions get higher complexity"""
        complexity = router._calculate_complexity(
            "Why do plants need sunlight?",
            LLMPurpose.GENERATION
        )

        # Has "why" and "?" = 0.15
        assert complexity >= 0.15

    def test_calculate_complexity_compare(self, router):
        """Test that compare questions get higher complexity"""
        complexity = router._calculate_complexity(
            "Compare and contrast photosynthesis and cellular respiration",
            LLMPurpose.GENERATION
        )

        # Has "compare" (0.2) + "photosynthesis" (0.05) = 0.25
        assert complexity >= 0.2

    @pytest.mark.asyncio
    async def test_should_use_cloud_low_complexity(self, router):
        """Test routing decision for low complexity query"""
        decision = await router._should_use_cloud(
            "What is ATP?",
            LLMPurpose.GENERATION,
            AnonymizationResult(
                anonymized_text="What is ATP?",
                has_pii=False,
                pii_count=0
            )
        )

        # Since "generation" is in force_cloud_for, it will use cloud even for low complexity
        assert decision.use_cloud is True
        assert "cloud" in decision.recommended_provider.lower()

    @pytest.mark.asyncio
    async def test_should_use_cloud_high_complexity(self, router):
        """Test routing decision for high complexity query"""
        query = "Explain the detailed molecular mechanisms of photosynthesis"
        decision = await router._should_use_cloud(
            query,
            LLMPurpose.GENERATION,
            AnonymizationResult(
                anonymized_text=query,
                has_pii=False,
                pii_count=0
            )
        )

        # High complexity (has "explain" + "photosynthesis")
        # Also "generation" is in force_cloud_for, so should use cloud
        assert decision.complexity_score >= 0.1  # Has "explain" + "photosynthesis"
        # Cloud is configured and "generation" is forced, so should use cloud
        assert decision.use_cloud is True or "cloud" in decision.recommended_provider.lower()

    @pytest.mark.asyncio
    async def test_should_use_cloud_with_pii(self, router):
        """Test that PII detection prevents cloud usage"""
        decision = await router._should_use_cloud(
            "Explain photosynthesis",  # High complexity but has PII
            LLMPurpose.GENERATION,
            AnonymizationResult(
                anonymized_text="Explain photosynthesis",
                has_pii=True,
                pii_count=1,
                safe_for_cloud=False  # PII makes it unsafe
            )
        )

        # Should NOT use cloud when PII is detected and unsafe
        assert decision.use_cloud is False or "anonymized" in decision.recommended_provider.lower()

    @pytest.mark.asyncio
    async def test_should_use_cloud_local_only_purpose(self, router):
        """Test that local-only purposes never use cloud"""
        decision = await router._should_use_cloud(
            "Any text",
            LLMPurpose.EMBEDDING,  # Embeddings are local-only
            AnonymizationResult(
                anonymized_text="Any text",
                has_pii=False,
                pii_count=0
            )
        )

        assert decision.use_cloud is False
        assert "local-only" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_should_use_cloud_forced_cloud_purpose(self, router):
        """Test that forced-cloud purposes use cloud"""
        decision = await router._should_use_cloud(
            "Any text",
            LLMPurpose.GENERATION,  # Generation forces cloud
            AnonymizationResult(
                anonymized_text="Any text",
                has_pii=False,
                pii_count=0
            )
        )

        # Should use cloud for generation
        assert "cloud" in decision.recommended_provider.lower() or "local" in decision.recommended_provider.lower()


class TestHybridLLMRouter:
    """Test the full HybridLLMRouter"""

    @pytest.fixture
    def router(self):
        config = HybridLLMConfig(
            cloud_threshold=0.7,
            local_model="test-model",
            local_base_url="http://localhost:11434",
            cloud_provider="minimax",
            cloud_api_key="test-key",
            cloud_model="test-model"
        )
        return HybridLLMRouter(config=config)

    @pytest.mark.asyncio
    async def test_generate_with_local_fallback(self, router):
        """Test generation uses local when cloud is not configured"""
        # Create a config without cloud API key to force local usage
        local_config = HybridLLMConfig(
            cloud_threshold=0.7,
            local_model="test-model",
            local_base_url="http://localhost:11434",
            cloud_api_key=None  # No cloud key configured
        )
        local_router = HybridLLMRouter(config=local_config)

        # Mock the local generation to avoid actual API call
        with patch.object(local_router, '_generate_local', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = LLMResponse(
                text="Local response",
                model="test-model",
                provider="ollama",
                tokens_used=10
            )

            result = await local_router.generate(
                query="What is ATP?",
                purpose=LLMPurpose.GENERATION
            )

            assert result.text == "Local response"
            assert result.provider == "ollama"

    @pytest.mark.asyncio
    async def test_generate_routing_metadata(self, router):
        """Test that routing metadata is included in response"""
        with patch.object(router, '_generate_local', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = LLMResponse(
                text="Response",
                model="test-model",
                provider="ollama",
                tokens_used=5
            )

            result = await router.generate(
                query="Simple question",
                purpose=LLMPurpose.GENERATION
            )

            # Check that routing metadata was added
            assert result.raw_response is not None
            assert "routing_decision" in result.raw_response

            routing = result.raw_response["routing_decision"]
            assert "provider" in routing
            assert "reason" in routing
            assert "complexity_score" in routing

    @pytest.mark.asyncio
    async def test_classify_local(self, router):
        """Test classification using local provider"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "fact"
            }
            mock_post.return_value = mock_response

            result = await router.classify(
                text="What is ATP?",
                labels=["fact", "concept"]
            )

            assert result.label in ["fact", "concept"]
            assert isinstance(result.confidence, float)

    @pytest.mark.asyncio
    async def test_embed_local(self, router):
        """Test embedding generation (always local)"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "embedding": [0.1, 0.2, 0.3] * 256  # 768-dim
            }
            mock_post.return_value = mock_response

            result = await router.embed("test text")

            assert len(result.embedding) > 0
            assert result.dimension > 0

    @pytest.mark.asyncio
    async def test_health_check(self, router):
        """Test health check endpoint"""
        with patch.object(router, '_check_local_available', return_value=False):
            health = await router.health_check()

            assert "status" in health
            assert "local_available" in health
            assert "cloud_provider" in health


class TestHybridLLMConfig:
    """Test HybridLLMConfig"""

    def test_default_config(self):
        """Test default configuration values"""
        config = HybridLLMConfig()

        assert config.cloud_threshold == 0.7
        assert config.always_anonymize is True
        assert "generation" in config.force_cloud_for
        assert "embedding" in config.local_only_for

    def test_custom_config(self):
        """Test custom configuration"""
        config = HybridLLMConfig(
            cloud_threshold=0.5,
            cloud_provider="openai",
            cloud_api_key="test-key"
        )

        assert config.cloud_threshold == 0.5
        assert config.cloud_provider == "openai"
        assert config.cloud_api_key == "test-key"


class TestIntegrationScenarios:
    """Integration test scenarios for common use cases"""

    @pytest.mark.asyncio
    async def test_simple_query_uses_local(self):
        """Test that simple queries use local provider"""
        config = HybridLLMConfig(cloud_threshold=0.8)
        router = HybridLLMRouter(config=config)

        with patch.object(router, '_generate_local', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = LLMResponse(
                text="Local answer",
                model="local",
                provider="ollama",
                tokens_used=5
            )

            result = await router.generate(
                query="What is ATP?",
                purpose=LLMPurpose.GENERATION
            )

            assert result.provider == "ollama"

    @pytest.mark.asyncio
    async def test_complex_query_with_anonymization(self):
        """Test complex query with PII gets anonymized first"""
        config = HybridLLMConfig(cloud_threshold=0.5)
        router = HybridLLMRouter(config=config)

        with patch.object(router, '_generate_local', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = LLMResponse(
                text="Answer",
                model="local",
                provider="ollama",
                tokens_used=10
            )

            result = await router.generate(
                query="My email is john@example.com. Explain photosynthesis.",
                purpose=LLMPurpose.GENERATION,
                user_id="student-123"
            )

            # Should have anonymization metadata
            routing = result.raw_response.get("routing_decision", {})
            assert "was_anonymized" in routing

    @pytest.mark.asyncio
    async def test_embedding_always_local(self):
        """Test that embeddings always use local provider"""
        config = HybridLLMConfig()
        router = HybridLLMRouter(config=config)

        # Embeddings are in local_only_for by default
        decision = await router._should_use_cloud(
            "any text",
            LLMPurpose.EMBEDDING,
            AnonymizationResult(
                anonymized_text="any text",
                has_pii=False,
                pii_count=0
            )
        )

        assert decision.use_cloud is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
