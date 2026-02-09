"""
OpenStax Embedding Service - Mu2 Cognitive OS
==============================================

Generates embeddings for textbook chunks using local Ollama.

Features:
- Uses embeddinggemma:300m (768 dimensions) via Ollama
- Batch processing for efficiency
- Stores in Supabase/pgvector format
- Tracks embedding metadata
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class EmbeddedChunk:
    """A chunk with its embedding vector"""
    chunk_id: str
    chapter_id: str
    book_id: str
    content: str
    title: str
    content_type: str
    embedding: List[float]  # 768-dimensional vector
    word_count: int
    key_concepts: List[str]
    definitions: Dict[str, str]
    section_title: Optional[str] = None
    source_location: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # For Supabase/pgvector
    def to_supabase_format(self) -> Dict[str, Any]:
        """Convert to Supabase pgvector format"""
        return {
            "chunk_id": self.chunk_id,
            "chapter_id": self.chapter_id,
            "book_id": self.book_id,
            "content": self.content,
            "title": self.title,
            "content_type": self.content_type,
            "embedding": self.embedding,  # pgvector will store as vector(768)
            "word_count": self.word_count,
            "key_concepts": self.key_concepts,
            "definitions": self.definitions,
            "section_title": self.section_title,
            "source_location": self.source_location,
            "metadata": self.metadata
        }


@dataclass
class EmbeddingResult:
    """Result of embedding chunks"""
    total_chunks: int
    successful_embeddings: int
    failed_embeddings: int
    embedded_chunks: List[EmbeddedChunk]
    processing_time_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class OllamaEmbeddingService:
    """
    Generates embeddings using Ollama's embeddinggemma:300m model

    Model: embeddinggemma:300m (768 dimensions)
    Runs locally via Ollama on http://localhost:11434
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "embeddinggemma:300m",
        batch_size: int = 3,  # Optimal: 100% success rate, fastest avg time
        timeout: int = 120
    ):
        """
        Initialize Ollama embedding service

        Args:
            base_url: Ollama API base URL
            model: Model name for embeddings
            batch_size: Number of chunks to embed in parallel
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.model = model
        self.batch_size = batch_size
        self.timeout = timeout

        # Verify Ollama is available
        self._verify_ollama()

    def _verify_ollama(self):
        """Verify Ollama is running and model is available"""
        import httpx

        try:
            # Check Ollama is running
            response = httpx.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()

            # Check if model is available
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            if self.model not in model_names:
                logger.warning(f"Model '{self.model}' not found in Ollama")
                logger.info(f"Available models: {model_names}")
                logger.info(f"Pull model with: ollama pull {self.model}")

        except Exception as e:
            logger.warning(f"Could not verify Ollama: {e}")
            logger.info("Make sure Ollama is running: ollama serve")

    async def embed_chunks(
        self,
        chunks: List[Any],  # TextChunk objects
        show_progress: bool = True
    ) -> EmbeddingResult:
        """
        Generate embeddings for a list of chunks

        Args:
            chunks: List of TextChunk objects
            show_progress: Whether to log progress

        Returns:
            EmbeddingResult with EmbeddedChunk objects
        """
        import time
        import httpx

        start_time = time.time()
        embedded_chunks = []
        successful = 0
        failed = 0

        if show_progress:
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            logger.info(f"  Model: {self.model}")
            logger.info(f"  Batch size: {self.batch_size}")

        # Process in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]

            if show_progress:
                logger.info(f"  Processing batch {i//self.batch_size + 1}/{(len(chunks) + self.batch_size - 1)//self.batch_size}...")

            # Create async tasks for batch
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                tasks = [
                    self._embed_single_chunk(chunk, client)
                    for chunk in batch
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result, chunk in zip(results, batch):
                    if isinstance(result, Exception):
                        failed += 1
                        # Log detailed error with chunk info
                        error_msg = str(result)
                        if not error_msg:
                            error_msg = result.__class__.__name__
                        logger.error(f"    ✗ Failed: {chunk.chunk_id} - {error_msg}")
                    else:
                        successful += 1
                        embedded_chunks.append(result)
                        if show_progress:
                            logger.info(f"    ✓ Embedded: {result.chunk_id}")

        processing_time = time.time() - start_time

        result = EmbeddingResult(
            total_chunks=len(chunks),
            successful_embeddings=successful,
            failed_embeddings=failed,
            embedded_chunks=embedded_chunks,
            processing_time_seconds=processing_time,
            metadata={
                "model": self.model,
                "embedding_dimension": 768,
                "batch_size": self.batch_size,
                "processed_at": datetime.now().isoformat()
            }
        )

        if show_progress:
            logger.info(f"\n✓ Embedded {successful}/{len(chunks)} chunks in {processing_time:.1f}s")
            logger.info(f"  Average: {processing_time/len(chunks):.2f}s per chunk")

        return result

    async def _embed_single_chunk(
        self,
        chunk: Any,  # TextChunk
        client: Any  # httpx.AsyncClient
    ) -> EmbeddedChunk:
        """Generate embedding for a single chunk"""

        try:
            # Prepare text for embedding (combine title + content)
            text_to_embed = f"{chunk.title}\n\n{chunk.content}"

            # Check if text is too long (Ollama has limits)
            if len(text_to_embed) > 100000:
                logger.warning(f"Chunk {chunk.chunk_id} is very long ({len(text_to_embed)} chars), truncating")
                text_to_embed = text_to_embed[:100000]

            # Call Ollama API (note: /api/embeddings endpoint, not /api/embed)
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text_to_embed
                }
            )
            response.raise_for_status()

            # Extract embedding (response has "embedding" key, not "embeddings")
            data = response.json()
            embedding = data.get("embedding", [])

            if not embedding:
                raise ValueError(f"No embedding returned for {chunk.chunk_id}. Response: {data}")

            # Create EmbeddedChunk
            embedded = EmbeddedChunk(
                chunk_id=chunk.chunk_id,
                chapter_id=chunk.chapter_id,
                book_id=chunk.book_id,
                content=chunk.content,
                title=chunk.title,
                content_type=chunk.content_type,
                embedding=embedding,
                word_count=chunk.get_word_count(),
                key_concepts=chunk.key_concepts,
                definitions=chunk.definitions,
                section_title=chunk.section_title,
                source_location=chunk.source_location,
                metadata={
                    "embedding_model": self.model,
                    "embedding_dimension": len(embedding),
                    "generated_at": datetime.now().isoformat()
                }
            )

            return embedded

        except Exception as e:
            # Re-raise with more context
            raise Exception(f"{chunk.chunk_id}: {type(e).__name__}: {str(e)}") from e

    def save_embeddings(
        self,
        result: EmbeddingResult,
        output_dir: str = None
    ) -> Path:
        """Save embeddings to JSON file"""
        from src.core.config import OPENSTAX_EMBEDDINGS_DIR

        if output_dir is None:
            output_dir = str(OPENSTAX_EMBEDDINGS_DIR)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save embeddings (without the full embedding array to save space)
        embeddings_file = output_path / f"{result.embedded_chunks[0].book_id}_embeddings.json"

        # Prepare data for JSON (convert embedding to list for JSON serialization)
        chunks_data = []
        for chunk in result.embedded_chunks:
            chunk_dict = {
                "chunk_id": chunk.chunk_id,
                "chapter_id": chunk.chapter_id,
                "book_id": chunk.book_id,
                "title": chunk.title,
                "content_type": chunk.content_type,
                "embedding_dimension": len(chunk.embedding),
                "embedding_preview": chunk.embedding[:5],  # First 5 values
                "word_count": chunk.word_count,
                "key_concepts": chunk.key_concepts,
                "definitions": chunk.definitions,
                "section_title": chunk.section_title,
                "source_location": chunk.source_location
            }
            chunks_data.append(chunk_dict)

        with open(embeddings_file, 'w') as f:
            json.dump({
                "metadata": result.metadata,
                "chunks": chunks_data
            }, f, indent=2)

        # Save full embeddings separately (for database import)
        full_embeddings_file = output_path / f"{result.embedded_chunks[0].book_id}_vectors.json"
        with open(full_embeddings_file, 'w') as f:
            # Format for Supabase pgvector import
            vectors_data = [
                {
                    "chunk_id": chunk.chunk_id,
                    "embedding": chunk.embedding,  # Full vector
                    "content": chunk.content[:1000] + "..." if len(chunk.content) > 1000 else chunk.content
                }
                for chunk in result.embedded_chunks
            ]
            json.dump(vectors_data, f)

        logger.info(f"Saved embeddings to: {embeddings_file}")
        logger.info(f"Saved vectors to: {full_embeddings_file}")

        return embeddings_file

    async def embed_and_store(
        self,
        chunks: List[Any],
        supabase_client=None,
        table_name: str = "textbook_chunks"
    ) -> EmbeddingResult:
        """
        Embed chunks and store in Supabase

        Args:
            chunks: List of TextChunk objects
            supabase_client: Optional Supabase client
            table_name: Table name for chunk storage

        Returns:
            EmbeddingResult
        """
        # Generate embeddings
        result = await self.embed_chunks(chunks, show_progress=True)

        # Store in Supabase if client provided
        if supabase_client:
            logger.info(f"\nStoring {len(result.embedded_chunks)} embeddings in Supabase...")

            try:
                # Store each chunk
                for i, embedded in enumerate(result.embedded_chunks):
                    # Convert to Supabase format
                    data = embedded.to_supabase_format()

                    # Insert into Supabase
                    response = supabase_client.table(table_name).insert(data).execute()

                    if (i + 1) % 10 == 0:
                        logger.info(f"  Stored {i + 1}/{len(result.embedded_chunks)} chunks")

                logger.info(f"✓ Stored all embeddings in Supabase table '{table_name}'")

            except Exception as e:
                logger.error(f"✗ Failed to store in Supabase: {e}")
                logger.info("  Embeddings saved locally instead")
                self.save_embeddings(result)

        return result


# Convenience functions
async def embed_chunks(chunks: List[Any]) -> EmbeddingResult:
    """Embed a list of chunks"""
    service = OllamaEmbeddingService()
    return await service.embed_chunks(chunks)


if __name__ == "__main__":
    # Test embedding service
    async def test_embedding():
        from dataclasses import dataclass

        # Create test chunks
        @dataclass
        class TestChunk:
            chunk_id: str
            chapter_id: str
            book_id: str
            title: str
            content: str
            content_type: str
            key_concepts: list
            definitions: dict
            section_title: str = None
            source_location: str = None

            def get_word_count(self):
                return len(self.content.split())

        test_chunks = [
            TestChunk(
                chunk_id="test_1",
                chapter_id="ch01",
                book_id="test_book",
                title="What is Government?",
                content="Government is the system through which a society makes and enforces public policies. Governments can be classified in several ways, including by who rules and by how power is distributed.",
                content_type="narrative",
                key_concepts=["government", "policy", "society"],
                definitions={"government": "The system through which a society makes and enforces public policies"},
                source_location="Chapter 1, Section 1.1"
            ),
            TestChunk(
                chunk_id="test_2",
                chapter_id="ch01",
                book_id="test_book",
                title="Types of Government",
                content="Democracy is a form of government in which the people hold the power. In a direct democracy, citizens vote directly on laws. In a representative democracy, citizens elect officials to make laws.",
                content_type="narrative",
                key_concepts=["democracy", "citizens", "laws"],
                definitions={"democracy": "A form of government in which the people hold the power"},
                source_location="Chapter 1, Section 1.2"
            )
        ]

        # Test embedding
        service = OllamaEmbeddingService()
        result = await service.embed_chunks(test_chunks, show_progress=True)

        print("\n" + "=" * 60)
        print("Embedding Test Results")
        print("=" * 60)
        print(f"Total chunks: {result.total_chunks}")
        print(f"Successful: {result.successful_embeddings}")
        print(f"Failed: {result.failed_embeddings}")
        print(f"Time: {result.processing_time_seconds:.1f}s")
        print()

        for chunk in result.embedded_chunks:
            print(f"Chunk: {chunk.chunk_id}")
            print(f"  Embedding dimension: {len(chunk.embedding)}")
            print(f"  Preview: {chunk.embedding[:3]}")
            print()

        # Save results if any embeddings succeeded
        if result.embedded_chunks:
            service.save_embeddings(result)
        else:
            print("No successful embeddings to save.")

    asyncio.run(test_embedding())
