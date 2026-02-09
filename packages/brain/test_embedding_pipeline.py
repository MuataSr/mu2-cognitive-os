"""
End-to-End Test: OpenStax Pipeline with Embeddings
==================================================

Tests the complete pipeline:
1. Extract chapter content from PDF
2. Chunk into learnable segments
3. Generate embeddings
4. Save embeddings for vector store
"""

import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_full_pipeline():
    """Test the full pipeline with embeddings"""
    from src.services.openstax_content_extractor import OpenStaxContentExtractor
    from src.services.openstax_chunk_processor import ChunkProcessor
    from src.services.openstax_embedding_service import OllamaEmbeddingService
    from src.services.openstax_pdf_splitter import ChapterPDF

    # Use the extracted American Government Chapter 1
    chapter_pdf_path = Path("/tmp/openstax_chapters/AmericanGovernment3e_chapter01_Chapter_1_American_Government_and_Civic_Engagement.pdf")

    if not chapter_pdf_path.exists():
        logger.error(f"Chapter PDF not found: {chapter_pdf_path}")
        logger.info("Please run test_local_pdfs.py first to extract chapters")
        return

    logger.info("=" * 60)
    logger.info("OpenStax Pipeline Test: Full with Embeddings")
    logger.info("=" * 60)

    # Create a ChapterPDF object
    chapter_pdf = ChapterPDF(
        chapter_number=1,
        title="Chapter 1 American Government and Civic Engagement",
        pdf_path=chapter_pdf_path,
        page_range=(17, 104),
        file_size=chapter_pdf_path.stat().st_size
    )

    # Step 1: Extract content
    logger.info("\nStep 1: Extracting content from chapter PDF...")
    extractor = OpenStaxContentExtractor()

    chapter_content = extractor.extract_chapter_content(
        chapter_pdf,
        "american-government-3e"
    )

    logger.info(f"  ✓ Title: {chapter_content.title}")
    logger.info(f"  ✓ Text length: {len(chapter_content.text_content):,} characters")
    logger.info(f"  ✓ Sections: {len(chapter_content.sections)}")
    logger.info(f"  ✓ Tables: {len(chapter_content.tables)}")

    # Step 2: Chunk content
    logger.info("\nStep 2: Chunking content into learnable segments...")
    processor = ChunkProcessor()

    chunking_result = processor.chunk_chapter_content(
        chapter_content,
        use_llm=False
    )

    logger.info(f"  ✓ Created {chunking_result.total_chunks} chunks")

    # Step 3: Generate embeddings
    logger.info("\nStep 3: Generating embeddings...")
    embedding_service = OllamaEmbeddingService(
        model="embeddinggemma:300m",
        batch_size=3  # Optimal: 100% success rate
    )

    embedding_result = await embedding_service.embed_chunks(
        chunking_result.chunks,
        show_progress=True
    )

    logger.info(f"\n  ✓ Generated {embedding_result.successful_embeddings}/{embedding_result.total_chunks} embeddings")
    logger.info(f"  ✓ Failed: {embedding_result.failed_embeddings}")
    logger.info(f"  ✓ Time: {embedding_result.processing_time_seconds:.1f}s")
    logger.info(f"  ✓ Average: {embedding_result.processing_time_seconds / embedding_result.total_chunks:.2f}s per chunk")

    # Step 4: Display sample embeddings
    logger.info("\nStep 4: Sample embeddings:")
    for i, chunk in enumerate(embedding_result.embedded_chunks[:3], 1):
        logger.info(f"\n  Chunk {i}: {chunk.chunk_id}")
        logger.info(f"    Title: {chunk.title[:60]}...")
        logger.info(f"    Dimension: {len(chunk.embedding)}")
        logger.info(f"    Preview: {chunk.embedding[:3]}")
        logger.info(f"    Concepts: {', '.join(chunk.key_concepts[:5])}")

    if embedding_result.total_chunks > 3:
        logger.info(f"\n  ... and {embedding_result.total_chunks - 3} more chunks")

    # Step 5: Save embeddings
    logger.info("\nStep 5: Saving embeddings...")
    embeddings_file = embedding_service.save_embeddings(embedding_result)
    logger.info(f"  ✓ Saved to: {embeddings_file}")

    # Summary statistics
    logger.info("\n" + "=" * 60)
    logger.info("Pipeline Summary")
    logger.info("=" * 60)

    word_counts = [c.get_word_count() for c in chunking_result.chunks]
    avg_word_count = sum(word_counts) / len(word_counts) if word_counts else 0

    content_types = {}
    for chunk in chunking_result.chunks:
        content_types[chunk.content_type] = content_types.get(chunk.content_type, 0) + 1

    logger.info(f"Source: {chapter_content.title}")
    logger.info(f"Total chunks: {chunking_result.total_chunks}")
    logger.info(f"Average chunk size: {avg_word_count:.0f} words")
    logger.info(f"Content types: {content_types}")
    logger.info(f"\nEmbeddings:")
    logger.info(f"  Model: {embedding_result.metadata.get('model')}")
    logger.info(f"  Dimension: {embedding_result.metadata.get('embedding_dimension')}")
    logger.info(f"  Generated: {embedding_result.successful_embeddings} embeddings")
    logger.info(f"  Processing time: {embedding_result.processing_time_seconds:.1f}s")

    total_concepts = sum(len(c.key_concepts) for c in chunking_result.chunks)
    total_definitions = sum(len(c.definitions) for c in chunking_result.chunks)
    logger.info(f"\nExtracted knowledge:")
    logger.info(f"  Total key concepts: {total_concepts}")
    logger.info(f"  Total definitions: {total_definitions}")

    logger.info("\n" + "=" * 60)
    logger.info("Next Steps:")
    logger.info("  1. Store embeddings in vector store (Supabase/pgvector)")
    logger.info("  2. Link concepts to knowledge graph")
    logger.info("  3. Test semantic search")
    logger.info("=" * 60)


if __name__ == "__main__":
    print("OpenStax Pipeline Test: Full Pipeline with Embeddings")
    print("=" * 60)
    print()

    asyncio.run(test_full_pipeline())
