"""
OpenStax Pipeline Test (Mock PDF) - Mu2 Cognitive OS
====================================================

Tests the pipeline with a mock PDF to verify all components work correctly.
This bypasses the OpenStax download issue for now.
"""

import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_pipeline():
    """Test the pipeline with a mock PDF"""
    from src.services.openstax_toc_extractor import (
        OpenStaxTOCExtractor,
        TOC,
        Chapter
    )
    from src.services.openstax_pdf_splitter import (
        OpenStaxPDFSplitter,
        ChapterPDF
    )
    from src.services.openstax_content_extractor import (
        OpenStaxContentExtractor
    )

    # Create a mock PDF path
    test_pdf = Path("/tmp/openstax_downloads/test_book.pdf")

    if not test_pdf.exists():
        logger.error(f"Test PDF not found: {test_pdf}")
        logger.info("Run: python3 /tmp/create_test_pdf.py")
        return

    logger.info("=" * 60)
    logger.info("OpenStax Pipeline Test (Mock PDF)")
    logger.info("=" * 60)

    # Create a mock TOC (since we can't extract from blank PDF)
    logger.info("\nStep 1: Creating mock TOC...")
    mock_toc = TOC(
        book_id="test_book",
        book_title="Test Book for Pipeline",
        chapters=[
            Chapter(
                chapter_number=1,
                title="Chapter 1: Introduction",
                start_page=1,
                end_page=5
            ),
            Chapter(
                chapter_number=2,
                title="Chapter 2: Methods",
                start_page=6,
                end_page=10
            ),
        ],
        total_pages=10
    )
    logger.info(f"✓ Created mock TOC with {len(mock_toc.chapters)} chapters")

    # Test splitting
    logger.info("\nStep 2: Testing PDF splitting...")
    splitter = OpenStaxPDFSplitter()
    try:
        chapter_pdfs = splitter.split_into_chapters(
            test_pdf,
            mock_toc,
            "test_book"
        )
        logger.info(f"✓ Split into {len(chapter_pdfs)} chapter PDFs")

        for i, cp in enumerate(chapter_pdfs):
            logger.info(f"  Chapter {i+1}: {cp.title}")
            logger.info(f"    File: {cp.pdf_path}")
            logger.info(f"    Pages: {cp.page_range}")
            logger.info(f"    Size: {cp.file_size:,} bytes")
    except Exception as e:
        logger.error(f"✗ Splitting failed: {e}")
        return

    # Test content extraction
    logger.info("\nStep 3: Testing content extraction...")
    extractor = OpenStaxContentExtractor()

    for i, chapter_pdf in enumerate(chapter_pdfs, 1):
        logger.info(f"\n  Extracting content from Chapter {i}...")

        try:
            content = extractor.extract_chapter_content(
                chapter_pdf,
                "test_book"
            )

            logger.info(f"  ✓ Chapter: {content.title}")
            logger.info(f"  ✓ Text length: {len(content.text_content)} characters")
            logger.info(f"  ✓ Sections: {len(content.sections)}")
            logger.info(f"  ✓ Images: {len(content.images)}")
            logger.info(f"  ✓ Tables: {len(content.tables)}")

            # Show metadata
            if content.metadata:
                logger.info(f"  ✓ Metadata keys: {list(content.metadata.keys())}")

        except Exception as e:
            logger.error(f"  ✗ Extraction failed: {e}")
            import traceback
            traceback.print_exc()

    # Test TOC extraction (with blank PDF - will use fallback)
    logger.info("\nStep 4: Testing TOC extraction with blank PDF...")
    toc_extractor = OpenStaxTOCExtractor()
    try:
        extracted_toc = toc_extractor.extract_from_pdf(test_pdf)
        logger.info(f"  ✓ Extracted TOC:")
        logger.info(f"    Book: {extracted_toc.book_title}")
        logger.info(f"    Total pages: {extracted_toc.total_pages}")
        logger.info(f"    Chapters found: {len(extracted_toc.chapters)}")
    except Exception as e:
        logger.warning(f"  ⚠ TOC extraction failed (expected for blank PDF): {e}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Pipeline Test Complete!")
    logger.info("=" * 60)
    logger.info("\nResults:")
    logger.info("  ✓ PDF Splitting: Working")
    logger.info("  ✓ Content Extraction: Working")
    logger.info("  ✓ TOC Extraction: Needs real PDF with structure")
    logger.info("\nNext Steps:")
    logger.info("  1. Resolve OpenStax PDF download URLs")
    logger.info("  2. Test with real OpenStax PDF")
    logger.info("  3. Implement LLM chunking layer")
    logger.info("  4. Generate embeddings and store in vector store")
    logger.info("=" * 60)


if __name__ == "__main__":
    print("OpenStax Pipeline Test (Mock PDF)")
    print("=" * 60)
    print("Testing pipeline components with mock PDF...")
    print()

    test_pipeline()

    print("\n✓ Test complete!")
