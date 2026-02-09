"""
Test embedding with different batch sizes to find optimal configuration
"""

import asyncio
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_batch_sizes():
    """Test embedding with different batch sizes"""
    from src.services.openstax_chunk_processor import ChunkProcessor
    from src.services.openstax_content_extractor import OpenStaxContentExtractor
    from src.services.openstax_embedding_service import OllamaEmbeddingService
    from src.services.openstax_pdf_splitter import ChapterPDF

    # Load a single chunk to test
    chapter_pdf_path = Path("/tmp/openstax_chapters/AmericanGovernment3e_chapter01_Chapter_1_American_Government_and_Civic_Engagement.pdf")

    if not chapter_pdf_path.exists():
        logger.error(f"Chapter PDF not found: {chapter_pdf_path}")
        return

    # Extract and chunk
    logger.info("Extracting and chunking content...")
    extractor = OpenStaxContentExtractor()
    chapter_pdf = ChapterPDF(
        chapter_number=1,
        title="Chapter 1",
        pdf_path=chapter_pdf_path,
        page_range=(17, 104),
        file_size=chapter_pdf_path.stat().st_size
    )

    chapter_content = extractor.extract_chapter_content(chapter_pdf, "american-government-3e")
    processor = ChunkProcessor()
    chunking_result = processor.chunk_chapter_content(chapter_content, use_llm=False)

    # Just test first 10 chunks for speed
    test_chunks = chunking_result.chunks[:10]

    # Test different batch sizes
    batch_sizes = [1, 2, 3, 5]

    for batch_size in batch_sizes:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing with batch_size={batch_size}")
        logger.info(f"{'=' * 60}")

        service = OllamaEmbeddingService(
            model="embeddinggemma:300m",
            batch_size=batch_size,
            timeout=120
        )

        result = await service.embed_chunks(test_chunks, show_progress=True)

        success_rate = (result.successful_embeddings / result.total_chunks) * 100
        logger.info(f"\nResults for batch_size={batch_size}:")
        logger.info(f"  Success: {result.successful_embeddings}/{result.total_chunks} ({success_rate:.1f}%)")
        logger.info(f"  Failed: {result.failed_embeddings}")
        logger.info(f"  Time: {result.processing_time_seconds:.1f}s")
        logger.info(f"  Avg per chunk: {result.processing_time_seconds / result.total_chunks:.2f}s")


if __name__ == "__main__":
    asyncio.run(test_batch_sizes())
