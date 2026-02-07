"""
Cloud LLM Providers for Mu2 Cognitive OS
Supports multiple cloud LLM providers including Minimax M2.1

This module provides a unified interface for calling various cloud LLM APIs
while maintaining FERPA compliance through prior anonymization.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

import httpx
from pydantic import BaseModel, Field


class LLMProviderType(Enum):
    """Supported LLM provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MINIMAX = "minimax"  # Minimax M2.1
    OPENROUTER = "openrouter"
    CUSTOM = "custom"


class LLMResponse(BaseModel):
    """Standard response from any LLM provider"""
    text: str = Field(..., description="Generated text response")
    model: str = Field(..., description="Model name used")
    provider: str = Field(..., description="Provider name")
    tokens_used: Optional[int] = Field(None, description="Tokens used for generation")
    finish_reason: Optional[str] = Field(None, description="Reason for completion")
    raw_response: Optional[Dict[str, Any]] = Field(None, description="Raw response from provider")


class LLMEmbedding(BaseModel):
    """Embedding response from any LLM provider"""
    embedding: List[float] = Field(..., description="Vector embedding")
    model: str = Field(..., description="Model name used")
    dimension: int = Field(..., description="Embedding dimension")


class LLMClassification(BaseModel):
    """Classification response from any LLM provider"""
    label: str = Field(..., description="Predicted label")
    confidence: float = Field(..., description="Confidence score")
    scores: Dict[str, float] = Field(default_factory=dict, description="All label scores")


class CloudLLMProvider(ABC):
    """
    Abstract base class for cloud LLM providers.

    All providers must implement these methods:
    - generate: Generate text completion
    - embed: Generate text embeddings
    - classify: Classify text into labels (optional)
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 30
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate text completion"""
        pass

    @abstractmethod
    async def embed(self, text: str) -> LLMEmbedding:
        """Generate text embedding"""
        pass

    async def classify(
        self,
        text: str,
        labels: List[str],
        prompt_template: Optional[str] = None
    ) -> LLMClassification:
        """
        Classify text into one of the provided labels.

        Default implementation uses generation with a classification prompt.
        Providers can override for native classification support.
        """
        if not prompt_template:
            prompt_template = """Classify the following text into one of these categories: {labels}

Text: {text}

Respond with only the category name."""

        prompt = prompt_template.format(
            labels=", ".join(labels),
            text=text
        )

        response = await self.generate(
            prompt,
            max_tokens=50,
            temperature=0.1  # Low temperature for consistent classification
        )

        # Extract label from response
        predicted_label = response.text.strip().lower()

        # Try to match against provided labels
        best_match = None
        best_score = 0.0

        for label in labels:
            if label.lower() in predicted_label:
                best_match = label
                best_score = 0.8
                break

        # If no match found, use first label as default
        if not best_match:
            best_match = labels[0]
            best_score = 0.3

        return LLMClassification(
            label=best_match,
            confidence=best_score,
            scores={label: 1.0 if label == best_match else 0.0 for label in labels}
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check if the provider is accessible"""
        try:
            # Simple generation test
            response = await self.generate("Hello", max_tokens=5)
            return {
                "status": "healthy",
                "provider": self.__class__.__name__,
                "model": self.model,
                "test_response_length": len(response.text)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.__class__.__name__,
                "error": str(e)
            }


class MinimaxProvider(CloudLLMProvider):
    """
    Minimax M2.1 Provider

    Minimax API Documentation:
    - Base URL: https://api.minimax.chat/v1
    - Models: abab6.5, abab5.5-chat, etc.
    - Supports: Text generation, embeddings, function calling
    """

    DEFAULT_BASE_URL = "https://api.minimax.chat/v1"
    DEFAULT_MODEL = "abab6.5s"  # M2.1 model
    EMBEDDING_MODEL = "embo-01"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        group_id: Optional[str] = None,
        timeout: int = 30
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url or self.DEFAULT_BASE_URL,
            model=model or self.DEFAULT_MODEL,
            timeout=timeout
        )
        self.group_id = group_id  # Required for some Minimax APIs

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.group_id:
            headers["GroupId"] = self.group_id
        return headers

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text using Minimax API.

        Args:
            prompt: The prompt text (or use messages for chat format)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            messages: Optional list of messages for chat format
        """
        client = await self._get_client()

        # Use chat format if messages provided, otherwise use simple prompt
        if messages is None:
            messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }

        if max_tokens:
            payload["tokens_to_generate"] = max_tokens

        # Add any additional parameters
        payload.update(kwargs)

        try:
            response = await client.post(
                f"{self.base_url}/text/chatcompletion_v2",
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()

            data = response.json()

            # Extract response text
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})

            return LLMResponse(
                text=text,
                model=self.model,
                provider="minimax",
                tokens_used=usage.get("total_tokens"),
                finish_reason=data.get("choices", [{}])[0].get("finish_reason"),
                raw_response=data
            )

        except httpx.HTTPError as e:
            raise Exception(f"Minimax API error: {str(e)}")

    async def embed(self, text: str) -> LLMEmbedding:
        """
        Generate embeddings using Minimax API.

        Note: Minimax embedding endpoint may vary based on API version.
        """
        client = await self._get_client()

        payload = {
            "model": self.EMBEDDING_MODEL,
            "texts": [text]
        }

        try:
            response = await client.post(
                f"{self.base_url}/text/embedding",
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()

            data = response.json()

            # Extract embedding vector
            embedding = data.get("vectors", [])[0] if data.get("vectors") else []

            return LLMEmbedding(
                embedding=embedding,
                model=self.EMBEDDING_MODEL,
                dimension=len(embedding)
            )

        except httpx.HTTPError as e:
            raise Exception(f"Minimax embedding error: {str(e)}")

    async def classify(
        self,
        text: str,
        labels: List[str],
        prompt_template: Optional[str] = None
    ) -> LLMClassification:
        """Classify text using Minimax"""
        return await super().classify(text, labels, prompt_template)


class OpenAIProvider(CloudLLMProvider):
    """
    OpenAI Provider (for comparison/alternative)

    Supports: GPT-4, GPT-3.5, etc.
    """

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o-mini"

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> LLMResponse:
        client = await self._get_client()

        if messages is None:
            messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return LLMResponse(
                text=text,
                model=self.model,
                provider="openai",
                tokens_used=usage.get("total_tokens"),
                finish_reason=data["choices"][0].get("finish_reason"),
                raw_response=data
            )

        except httpx.HTTPError as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def embed(self, text: str) -> LLMEmbedding:
        client = await self._get_client()

        payload = {
            "model": self.model or "text-embedding-3-small",
            "input": text
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["data"][0]["embedding"]

            return LLMEmbedding(
                embedding=embedding,
                model=self.model or "text-embedding-3-small",
                dimension=len(embedding)
            )

        except httpx.HTTPError as e:
            raise Exception(f"OpenAI embedding error: {str(e)}")


class CustomProvider(CloudLLMProvider):
    """
    Custom OpenAI-compatible provider.

    Can be used with any OpenAI-compatible API including:
    - Local vLLM deployments
    - Other cloud providers
    - Custom endpoints
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 30
    ):
        super().__init__(api_key, base_url, model, timeout)

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> LLMResponse:
        client = await self._get_client()

        if messages is None:
            messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return LLMResponse(
                text=text,
                model=self.model,
                provider="custom",
                tokens_used=usage.get("total_tokens"),
                finish_reason=data.get("choices", [{}])[0].get("finish_reason"),
                raw_response=data
            )

        except httpx.HTTPError as e:
            raise Exception(f"Custom provider API error: {str(e)}")

    async def embed(self, text: str) -> LLMEmbedding:
        client = await self._get_client()

        payload = {
            "model": self.model,
            "input": text
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["data"][0]["embedding"]

            return LLMEmbedding(
                embedding=embedding,
                model=self.model,
                dimension=len(embedding)
            )

        except httpx.HTTPError as e:
            raise Exception(f"Custom provider embedding error: {str(e)}")


def create_provider(
    provider_type: Union[str, LLMProviderType],
    api_key: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> CloudLLMProvider:
    """
    Factory function to create a cloud LLM provider.

    Args:
        provider_type: Type of provider (openai, minimax, custom, etc.)
        api_key: API key for authentication
        base_url: Optional custom base URL
        model: Model name to use
        **kwargs: Additional provider-specific arguments

    Returns:
        CloudLLMProvider instance

    Example:
        ```python
        # Minimax M2.1
        provider = create_provider(
            provider_type="minimax",
            api_key="your-minimax-api-key",
            model="abab6.5s"
        )

        # Custom endpoint
        provider = create_provider(
            provider_type="custom",
            api_key="your-api-key",
            base_url="https://your-endpoint.com/v1",
            model="your-model"
        )
        ```
    """
    if isinstance(provider_type, str):
        try:
            provider_type = LLMProviderType(provider_type.lower())
        except ValueError:
            raise ValueError(f"Unknown provider type: {provider_type}")

    providers = {
        LLMProviderType.OPENAI: OpenAIProvider,
        LLMProviderType.MINIMAX: MinimaxProvider,
        LLMProviderType.CUSTOM: CustomProvider,
        # Add more providers as needed
    }

    provider_class = providers.get(provider_type, CustomProvider)

    # Custom provider requires base_url
    if provider_type == LLMProviderType.CUSTOM and not base_url:
        raise ValueError("Custom provider requires base_url")

    return provider_class(
        api_key=api_key,
        base_url=base_url,
        model=model,
        **kwargs
    )
