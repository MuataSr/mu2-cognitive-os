"""
OpenStax Ingestion Pipeline Test - Mu2 Cognitive OS
==================================================

Tests the complete textbook ingestion pipeline:
1. Download PDF from OpenStax
2. Extract table of contents (TOC)
3. Split into chapter PDFs
4. Extract structured content (text, images, tables, sections)
5. Display results for verification

This is a prototype test before full vector store integration.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_single_book_pipeline(
    book_id: str = "american-government-2e",
    max_chapters: int = 2  # Only process first 2 chapters for testing
):
    """
    Test the full pipeline with a single OpenStax book

    Args:
        book_id: OpenStax book identifier
        max_chapters: Maximum number of chapters to process (for testing)
    """
    from src.services.openstax_downloader import (
        OpenStaxDownloader,
        OPENSTAX_BOOKS
    )
    from src.services.openstax_toc_extractor import OpenStaxTOCExtractor
    from src.services.openstax_pdf_splitter import OpenStaxPDFSplitter
    from src.services.openstax_content_extractor import OpenStaxContentExtractor

    # Get book metadata
    if book_id not in OPENSTAX_BOOKS:
        logger.error(f"Unknown book_id: {book_id}")
        logger.info(f"Available books: {list(OPENSTAX_BOOKS.keys())}")
        return

    book = OPENSTAX_BOOKS[book_id]
    logger.info(f"{'='*60}")
    logger.info(f"Testing OpenStax Ingestion Pipeline")
    logger.info(f"{'='*60}")
    logger.info(f"Book: {book.title}")
    logger.info(f"Subject: {book.subject}")
    logger.info(f"Grade Level: {book.grade_level}")
    logger.info(f"Florida Standard: {book.florida_standard}")
    logger.info(f"{'='*60}\n")

    # Step 1: Download PDF
    logger.info("Step 1: Downloading PDF from OpenStax...")
    downloader = OpenStaxDownloader()
    pdf_path = await downloader.download_pdf(book)

    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    logger.info(f"✓ Downloaded: {pdf_path.name} ({file_size_mb:.2f} MB)\n")

    # Step 2: Extract TOC
    logger.info("Step 2: Extracting Table of Contents...")
    toc_extractor = OpenStaxTOCExtractor()
    toc = toc_extractor.extract_from_pdf(pdf_path)

    logger.info(f"✓ Book Title: {toc.book_title}")
    logger.info(f"✓ Total Pages: {toc.total_pages}")
    logger.info(f"✓ Chapters Found: {len(toc.chapters)}")

    # Show first few chapters
    logger.info("\nFirst 5 chapters:")
    for chapter in toc.chapters[:5]:
        logger.info(f"  Chapter {chapter.chapter_number}: {chapter.title}")
        logger.info(f"    Pages: {chapter.start_page}-{chapter.end_page}")
    logger.info("")

    # Step 3: Split into chapter PDFs
    logger.info("Step 3: Splitting PDF into chapters...")
    splitter = OpenStaxPDFSplitter()
    chapter_pdfs = splitter.split_into_chapters(pdf_path, toc, book_id)

    logger.info(f"✓ Created {len(chapter_pdfs)} chapter PDFs")

    # Limit chapters for testing
    if max_chapters and len(chapter_pdfs) > max_chapters:
        chapter_pdfs = chapter_pdfs[:max_chapters]
        logger.info(f"  (Testing with first {max_chapters} chapters only)\n")
    else:
        logger.info("")

    # Step 4: Extract content from each chapter
    logger.info("Step 4: Extracting structured content...")
    extractor = OpenStaxContentExtractor()

    for i, chapter_pdf in enumerate(chapter_pdfs, 1):
        logger.info(f"\nProcessing Chapter {i}/{len(chapter_pdfs)}: {chapter_pdf.title}")

        try:
            content = extractor.extract_chapter_content(chapter_pdf, book_id)

            # Display results
            text_length = len(content.text_content)
            logger.info(f"  Title: {content.title}")
            logger.info(f"  Text Length: {text_length:,} characters")
            logger.info(f"  Sections: {len(content.sections)}")
            logger.info(f"  Images: {len(content.images)}")
            logger.info(f"  Tables: {len(content.tables)}")

            # Show sections
            if content.sections:
                logger.info(f"  Section Structure:")
                for section in content.sections[:5]:
                    indent = "  " * (section.level - 1)
                    logger.info(f"    {indent}• {section.title}")
                if len(content.sections) > 5:
                    logger.info(f"    ... and {len(content.sections) - 5} more")

            # Show images
            if content.images:
                logger.info(f"  Images:")
                for img in content.images[:3]:
                    logger.info(f"    • {img.image_id}: page {img.page_number}")
                if len(content.images) > 3:
                    logger.info(f"    ... and {len(content.images) - 3} more")

            # Show tables
            if content.tables:
                logger.info(f"  Tables:")
                for table in content.tables[:3]:
                    logger.info(f"    • {table.table_id}: {len(table.headers)} columns, {len(table.rows)} rows")
                if len(content.tables) > 3:
                    logger.info(f"    ... and {len(content.tables) - 3} more")

            # Show sample text (first 200 chars)
            sample_text = content.get_full_text()[:200]
            logger.info(f"  Sample Text: \"{sample_text}...\"")

            logger.info(f"  ✓ Extraction complete")

        except Exception as e:
            logger.error(f"  ✗ Error extracting chapter: {e}")

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"Pipeline Test Complete!")
    logger.info(f"{'='*60}")
    logger.info(f"Output Locations:")
    logger.info(f"  Downloaded PDF: {pdf_path}")
    logger.info(f"  Chapter PDFs: {splitter.output_dir}")
    logger.info(f"  Extracted Images: {extractor.assets_dir}")
    logger.info(f"\nNext Steps:")
    logger.info(f"  1. Review extracted content for accuracy")
    logger.info(f"  2. Implement LLM chunking strategy")
    logger.info(f"  3. Generate embeddings")
    logger.info(f"  4. Store in vector store (Supabase)")
    logger.info(f"{'='*60}\n")

    return {
        "pdf_path": pdf_path,
        "toc": toc,
        "chapter_pdfs": chapter_pdfs,
    }


async def test_multiple_books():
    """Test pipeline with multiple books"""
    books_to_test = [
        "american-government-2e",  # Civics EOC - critical
        "prealgebra-2e",           # Math foundation
    ]

    results = {}

    for book_id in books_to_test:
        logger.info(f"\n\n{'#'*60}")
        logger.info(f"Testing Book: {book_id}")
        logger.info(f"{'#'*60}\n")

        try:
            result = await test_single_book_pipeline(book_id, max_chapters=1)
            results[book_id] = result
        except Exception as e:
            logger.error(f"Failed to process {book_id}: {e}")
            results[book_id] = None

    return results


if __name__ == "__main__":
    # Run test
    print("OpenStax Ingestion Pipeline Test")
    print("=" * 60)
    print()

    # Test single book (Developmental Math - smaller PDF for testing)
    # After testing works, switch to american-government-2e for Civics EOC
    result = asyncio.run(test_single_book_pipeline(
        book_id="prealgebra-2e",  # Try Prealgebra first (smaller PDF)
        max_chapters=1  # Only process first chapter
    ))

    # Uncomment to test with American Government (large PDF - may timeout):
    # result = asyncio.run(test_single_book_pipeline(
    #     book_id="american-government-2e",
    #     max_chapters=2
    # ))

    # Uncomment to test multiple books:
    # results = asyncio.run(test_multiple_books())

    print("\n✓ Test complete! Check output above for results.")
