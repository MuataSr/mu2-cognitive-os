"""
Hybrid LLM Router for Mu2 Cognitive OS
Intelligent routing between local and cloud LLMs

This router decides whether to use:
1. Local Ollama (for simple queries, privacy-sensitive content, or offline mode)
2. Cloud LLM (for complex queries requiring higher quality)

Decision factors:
- Query complexity (length, structure)
- PII detection (if PII found, only use local or anonymized cloud)
- User preferences
- Service availability
"""

import asyncio
from typing import Literal, Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

from src.core.config import settings
from src.services.anonymization_service import AnonymizationService, AnonymizationResult
from src.services.cloud_llm_providers import (
    CloudLLMProvider,
    create_provider,
    LLMProviderType,
    LLMResponse,
    LLMEmbedding,
    LLMClassification
)
from src.services.pii_patterns import detect_pii


class LLMPurpose(Enum):
    """Purpose of the LLM call"""
    GENERATION = "generation"  # Response generation
    CLASSIFICATION = "classification"  # Query routing, sentiment, etc.
    EMBEDDING = "embedding"  # Vector embeddings
    ROUTING = "routing"  # Decision making


@dataclass
class RoutingDecision:
    """Result of routing decision"""
    use_cloud: bool
    reason: str
    complexity_score: float
    pii_detected: bool
    recommended_provider: str
    confidence: float


class HybridLLMConfig(BaseModel):
    """Configuration for hybrid LLM routing"""
    # Local LLM settings (Ollama)
    local_provider: str = "ollama"
    local_model: str = "gemma3:1b"
    local_base_url: str = "http://localhost:11434"

    # Cloud LLM settings
    cloud_provider: str = "minimax"  # Default to Minimax
    cloud_api_key: Optional[str] = None
    cloud_base_url: Optional[str] = None
    cloud_model: Optional[str] = None
    cloud_group_id: Optional[str] = None  # For Minimax

    # Routing thresholds
    cloud_threshold: float = 0.7  # Complexity threshold for cloud
    always_anonymize: bool = True  # Always anonymize before cloud
    allow_cloud_fallback: bool = True

    # Purpose-specific routing
    force_cloud_for: List[str] = Field(default_factory=lambda: ["generation"])
    local_only_for: List[str] = Field(default_factory=lambda: ["embedding"])

    # Anonymization settings
    anonymization_enabled: bool = True
    anonymization_method: str = "hybrid"


class HybridLLMRouter:
    """
    Router for hybrid local/cloud LLM usage.

    Decision Flow:
    1. Check if query requires specific provider (forced or local-only)
    2. Anonymize input if enabled
    3. Assess complexity
    4. Make routing decision
    5. Execute with chosen provider
    6. Handle fallbacks
    """

    def __init__(self, config: Optional[HybridLLMConfig] = None):
        self.config = config or HybridLLMConfig()
        self.anonymizer = AnonymizationService(
            method=self.config.anonymization_method
        )
        self._cloud_provider: Optional[CloudLLMProvider] = None
        self._local_available = None

    async def _get_cloud_provider(self) -> CloudLLMProvider:
        """Get or create cloud provider instance"""
        if self._cloud_provider is None:
            if not self.config.cloud_api_key:
                raise ValueError("Cloud API key not configured")

            # Build provider kwargs - only pass group_id for minimax
            provider_kwargs = {
                "api_key": self.config.cloud_api_key,
                "base_url": self.config.cloud_base_url,
                "model": self.config.cloud_model,
            }

            # Only pass group_id for minimax provider
            if self.config.cloud_provider == "minimax" and self.config.cloud_group_id:
                provider_kwargs["group_id"] = self.config.cloud_group_id

            # Create provider based on type
            self._cloud_provider = create_provider(
                provider_type=self.config.cloud_provider,
                **provider_kwargs
            )

        return self._cloud_provider

    async def _check_local_available(self) -> bool:
        """Check if local Ollama is available"""
        if self._local_available is not None:
            return self._local_available

        try:
            import requests
            response = requests.get(f"{self.config.local_base_url}/api/tags", timeout=2)
            self._local_available = response.status_code == 200
        except Exception:
            self._local_available = False

        return self._local_available

    def _calculate_complexity(self, text: str, purpose: LLMPurpose) -> float:
        """
        Calculate query complexity score (0-1).

        Factors:
        - Length (longer = more complex)
        - Sentence structure
        - Question complexity
        - Domain-specific terms
        """
        score = 0.0

        # Length factor (0-0.3)
        word_count = len(text.split())
        if word_count > 100:
            score += 0.3
        elif word_count > 50:
            score += 0.2
        elif word_count > 20:
            score += 0.1

        # Structural complexity (0-0.3)
        if "?" in text and "why" in text.lower():
            score += 0.15  # "Why" questions are more complex
        if "?" in text and "how" in text.lower():
            score += 0.15  # "How" questions
        if "compare" in text.lower() or "contrast" in text.lower():
            score += 0.2
        if "explain" in text.lower():
            score += 0.1

        # Multi-part questions (0-0.2)
        if text.count("?") > 1:
            score += 0.2

        # Domain complexity indicators (0-0.2)
        complex_terms = [
            "photosynthesis", "mitochondria", "electron", "molecule",
            "chemical", "reaction", "equation", "theoretical", "analyze"
        ]
        for term in complex_terms:
            if term in text.lower():
                score += 0.05
                score = min(score, 1.0)
                break

        return min(score, 1.0)

    async def _should_use_cloud(
        self,
        query: str,
        purpose: LLMPurpose,
        anonymized_result: Optional[AnonymizationResult] = None
    ) -> RoutingDecision:
        """
        Decide whether to use cloud LLM based on multiple factors.
        """
        # Check if cloud is even configured
        cloud_configured = bool(self.config.cloud_api_key)

        # If cloud is not configured, always use local
        if not cloud_configured:
            return RoutingDecision(
                use_cloud=False,
                reason="Cloud API key not configured, using local",
                complexity_score=0.0,
                pii_detected=anonymized_result.has_pii if anonymized_result else False,
                recommended_provider="local (no cloud key)",
                confidence=1.0
            )

        # Check purpose-specific routing
        if purpose.value in self.config.local_only_for:
            return RoutingDecision(
                use_cloud=False,
                reason=f"Local-only for purpose: {purpose.value}",
                complexity_score=0.0,
                pii_detected=anonymized_result.has_pii if anonymized_result else False,
                recommended_provider="local",
                confidence=1.0
            )

        if purpose.value in self.config.force_cloud_for:
            # Still check if PII is present
            if anonymized_result and anonymized_result.has_pii:
                if self.config.always_anonymize and anonymized_result.safe_for_cloud:
                    return RoutingDecision(
                        use_cloud=True,
                        reason=f"Forced cloud for {purpose.value}, PII anonymized",
                        complexity_score=1.0,
                        pii_detected=True,
                        recommended_provider="cloud (anonymized)",
                        confidence=0.9
                    )
                else:
                    return RoutingDecision(
                        use_cloud=False,
                        reason=f"PII detected, cannot use cloud for {purpose.value}",
                        complexity_score=0.0,
                        pii_detected=True,
                        recommended_provider="local",
                        confidence=1.0
                    )
            else:
                return RoutingDecision(
                    use_cloud=True,
                    reason=f"Forced cloud for purpose: {purpose.value}",
                    complexity_score=1.0,
                    pii_detected=False,
                    recommended_provider="cloud",
                    confidence=1.0
                )

        # Calculate complexity
        complexity = self._calculate_complexity(query, purpose)

        # Check PII
        has_pii = anonymized_result.has_pii if anonymized_result else False
        pii_unsafe = anonymized_result and not anonymized_result.safe_for_cloud

        # Decision based on complexity
        if complexity >= self.config.cloud_threshold:
            if pii_unsafe:
                return RoutingDecision(
                    use_cloud=False,
                    reason="High complexity but PII detected, using local",
                    complexity_score=complexity,
                    pii_detected=True,
                    recommended_provider="local (PII safety)",
                    confidence=0.8
                )
            else:
                return RoutingDecision(
                    use_cloud=True,
                    reason=f"High complexity ({complexity:.2f} >= {self.config.cloud_threshold})",
                    complexity_score=complexity,
                    pii_detected=has_pii,
                    recommended_provider="cloud" if not has_pii else "cloud (anonymized)",
                    confidence=min(complexity + 0.2, 1.0)
                )

        # Medium complexity - consider other factors
        if complexity >= 0.4:
            if await self._check_local_available():
                return RoutingDecision(
                    use_cloud=False,
                    reason=f"Medium complexity, local available and sufficient",
                    complexity_score=complexity,
                    pii_detected=has_pii,
                    recommended_provider="local",
                    confidence=0.7
                )
            else:
                if not pii_unsafe:
                    return RoutingDecision(
                        use_cloud=True,
                        reason="Local unavailable, falling back to cloud",
                        complexity_score=complexity,
                        pii_detected=has_pii,
                        recommended_provider="cloud (fallback)",
                        confidence=0.6
                    )

        # Low complexity - use local
        return RoutingDecision(
            use_cloud=False,
            reason=f"Low complexity ({complexity:.2f}), local sufficient",
            complexity_score=complexity,
            pii_detected=has_pii,
            recommended_provider="local",
            confidence=0.9
        )

    async def generate(
        self,
        query: str,
        context: Optional[str] = None,
        purpose: LLMPurpose = LLMPurpose.GENERATION,
        user_id: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text response using hybrid routing.

        Args:
            query: The input query
            context: Optional context to include
            purpose: Purpose of the generation
            user_id: Optional user ID for anonymization
            **kwargs: Additional parameters for LLM

        Returns:
            LLMResponse with generated text and metadata
        """
        # Step 1: Anonymize if enabled
        anonymized_result = None
        working_query = query

        if self.config.anonymization_enabled:
            anonymized_result = await self.anonymizer.anonymize_text(query, user_id)
            working_query = anonymized_result.anonymized_text

        # Step 2: Make routing decision
        decision = await self._should_use_cloud(working_query, purpose, anonymized_result)

        # Step 3: Generate with chosen provider
        try:
            if decision.use_cloud:
                response = await self._generate_cloud(working_query, context, **kwargs)
                response_provider = "cloud"
            else:
                response = await self._generate_local(working_query, context, **kwargs)
                response_provider = "local"

            # Add routing metadata
            response.raw_response = response.raw_response or {}
            response.raw_response.update({
                "routing_decision": {
                    "provider": response_provider,
                    "reason": decision.reason,
                    "complexity_score": decision.complexity_score,
                    "pii_detected": decision.pii_detected,
                    "was_anonymized": anonymized_result.has_pii if anonymized_result else False
                }
            })

            return response

        except Exception as e:
            # Fallback logic
            response_provider = "cloud" if decision.use_cloud else "local"
            if decision.use_cloud and self.config.allow_cloud_fallback:
                try:
                    # Try local as fallback
                    response = await self._generate_local(query, context, **kwargs)
                    response.raw_response = response.raw_response or {}
                    response.raw_response["fallback"] = "cloud_failed"
                    return response
                except Exception:
                    pass

            raise Exception(f"Generation failed (provider: {response_provider}): {str(e)}")

    async def _generate_cloud(
        self,
        query: str,
        context: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate using cloud provider"""
        provider = await self._get_cloud_provider()

        # Build prompt with context
        prompt = query
        if context:
            prompt = f"Context:\n{context}\n\nQuery:\n{query}"

        response = await provider.generate(
            prompt=prompt,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 500)
        )

        return response

    async def _generate_local(
        self,
        query: str,
        context: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate using local Ollama"""
        import requests

        # Build prompt with context
        prompt = query
        if context:
            prompt = f"Context: {context}\n\nQuestion: {query}"

        response = requests.post(
            f"{self.config.local_base_url}/api/generate",
            json={
                "model": self.config.local_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 500)
                }
            },
            timeout=60
        )
        response.raise_for_status()

        data = response.json()

        return LLMResponse(
            text=data.get("response", ""),
            model=self.config.local_model,
            provider="ollama",
            tokens_used=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            raw_response=data
        )

    async def classify(
        self,
        text: str,
        labels: List[str],
        purpose: LLMPurpose = LLMPurpose.CLASSIFICATION
    ) -> LLMClassification:
        """Classify text using appropriate provider"""
        # For classification, prefer local for speed
        decision = await self._should_use_cloud(text, purpose)

        if decision.use_cloud:
            provider = await self._get_cloud_provider()
            return await provider.classify(text, labels)
        else:
            # Local classification using Ollama
            import requests

            prompt = f"Classify the following text into one of these categories: {', '.join(labels)}\n\nText: {text}\n\nRespond with only the category name."

            response = requests.post(
                f"{self.config.local_base_url}/api/generate",
                json={
                    "model": self.config.local_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            result_text = data.get("response", "").strip().lower()

            # Find best match
            best_label = labels[0]
            best_score = 0.3

            for label in labels:
                if label.lower() in result_text:
                    best_label = label
                    best_score = 0.8
                    break

            return LLMClassification(
                label=best_label,
                confidence=best_score,
                scores={label: 1.0 if label == best_label else 0.0 for label in labels}
            )

    async def embed(self, text: str) -> LLMEmbedding:
        """Generate embeddings (always local for privacy)"""
        import requests

        response = requests.post(
            f"{self.config.local_base_url}/api/embeddings",
            json={
                "model": settings.embedding_model,
                "prompt": text
            },
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        embedding = data.get("embedding", [])

        return LLMEmbedding(
            embedding=embedding,
            model=settings.embedding_model,
            dimension=len(embedding)
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all providers"""
        local_available = await self._check_local_available()

        cloud_health = {"status": "not_configured"}
        if self.config.cloud_api_key:
            try:
                provider = await self._get_cloud_provider()
                cloud_health = await provider.health_check()
            except Exception as e:
                cloud_health = {"status": "unhealthy", "error": str(e)}

        anonymizer_health = await self.anonymizer.health_check()

        return {
            "status": "healthy" if local_available or cloud_health.get("status") == "healthy" else "degraded",
            "local_available": local_available,
            "local_model": self.config.local_model,
            "cloud_provider": self.config.cloud_provider,
            "cloud_health": cloud_health,
            "anonymization": anonymizer_health,
            "config": {
                "cloud_threshold": self.config.cloud_threshold,
                "anonymization_enabled": self.config.anonymization_enabled,
                "force_cloud_for": self.config.force_cloud_for,
                "local_only_for": self.config.local_only_for
            }
        }


# Global singleton instance
hybrid_router = HybridLLMRouter(
    config=HybridLLMConfig(
        local_provider=settings.llm_provider,
        local_model=settings.llm_model,
        local_base_url=settings.llm_base_url,
        cloud_provider=settings.llm_cloud_provider,
        cloud_api_key=settings.llm_cloud_api_key,
        cloud_base_url=settings.llm_cloud_base_url,
        cloud_model=settings.llm_cloud_model,
        cloud_group_id=settings.llm_cloud_group_id if settings.llm_cloud_provider == "minimax" else None,
        cloud_threshold=settings.llm_cloud_threshold,
        force_cloud_for=settings.llm_force_cloud_for,
        local_only_for=settings.llm_local_only_for,
        anonymization_enabled=settings.llm_anonymization_enabled,
        anonymization_method=settings.anonymization_method,
    )
)
