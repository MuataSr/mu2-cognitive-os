"""
End-to-End Test: OpenStax Pipeline with Chunking
==================================================

Tests the complete pipeline:
1. Extract chapter content from PDF
2. Chunk into learnable segments
3. Display results
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
    """Test the full pipeline with extracted chapter PDF"""
    from src.services.openstax_content_extractor import OpenStaxContentExtractor
    from src.services.openstax_chunk_processor import ChunkProcessor
    from src.services.openstax_pdf_splitter import ChapterPDF

    # Use the extracted American Government Chapter 1
    chapter_pdf_path = Path("/tmp/openstax_chapters/AmericanGovernment3e_chapter01_Chapter_1_American_Government_and_Civic_Engagement.pdf")

    if not chapter_pdf_path.exists():
        logger.error(f"Chapter PDF not found: {chapter_pdf_path}")
        logger.info("Please run test_local_pdfs.py first to extract chapters")
        return

    logger.info("=" * 60)
    logger.info("OpenStax Pipeline Test: Chunking")
    logger.info("=" * 60)

    # Create a ChapterPDF object
    chapter_pdf = ChapterPDF(
        chapter_number=1,
        title="Chapter 1 American Government and Civic Engagement",
        pdf_path=chapter_pdf_path,
        page_range=(17, 104),  # From our earlier extraction
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
        use_llm=False  # Set to True to enable LLM enrichment
    )

    logger.info(f"  ✓ Created {chunking_result.total_chunks} chunks")

    # Step 3: Display chunk results
    logger.info("\nStep 3: Chunk analysis:")
    logger.info("")

    for i, chunk in enumerate(chunking_result.chunks[:10], 1):  # Show first 10
        logger.info(f"Chunk {i}/{chunking_result.total_chunks}: {chunk.title[:60]}...")
        logger.info(f"  Type: {chunk.content_type}")
        logger.info(f"  Words: {chunk.get_word_count()}")
        logger.info(f"  Concepts: {', '.join(chunk.key_concepts[:5])}")
        if chunk.definitions:
            logger.info(f"  Definitions: {', '.join(list(chunk.definitions.keys())[:3])}")
        logger.info(f"  Preview: {chunk.content[:100]}...")
        logger.info("")

    if chunking_result.total_chunks > 10:
        logger.info(f"... and {chunking_result.total_chunks - 10} more chunks")
        logger.info("")

    # Step 4: Save chunks
    logger.info("\nStep 4: Saving chunks...")
    chunks_file = processor.save_chunks(chunking_result)
    logger.info(f"  ✓ Saved to: {chunks_file}")

    # Summary statistics
    logger.info("\n" + "=" * 60)
    logger.info("Pipeline Summary")
    logger.info("=" * 60)

    word_counts = [c.get_word_count() for c in chunking_result.chunks]
    avg_word_count = sum(word_counts) / len(word_counts) if word_counts else 0

    content_types = {}
    for chunk in chunking_result.chunks:
        content_types[chunk.content_type] = content_types.get(chunk.content_type, 0) + 1

    logger.info(f"Total chunks: {chunking_result.total_chunks}")
    logger.info(f"Average chunk size: {avg_word_count:.0f} words")
    logger.info(f"Content types: {content_types}")

    total_concepts = sum(len(c.key_concepts) for c in chunking_result.chunks)
    total_definitions = sum(len(c.definitions) for c in chunking_result.chunks)
    logger.info(f"Total key concepts: {total_concepts}")
    logger.info(f"Total definitions: {total_definitions}")

    logger.info("\n" + "=" * 60)
    logger.info("Next Steps:")
    logger.info("  1. Generate embeddings for each chunk")
    logger.info("  2. Store in vector store (Supabase/pgvector)")
    logger.info("  3. Link to knowledge graph")
    logger.info("=" * 60)


if __name__ == "__main__":
    print("OpenStax Pipeline Test: Full Pipeline with Chunking")
    print("=" * 60)
    print()

    asyncio.run(test_full_pipeline())
