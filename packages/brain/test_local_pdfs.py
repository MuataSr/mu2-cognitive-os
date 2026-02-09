"""
OpenStax Pipeline Test (Local PDFs) - Mu2 Cognitive OS
======================================================

Process OpenStax PDFs that you've manually downloaded.

Instructions:
1. Download OpenStax PDFs to: ~/Downloads/openstax_pdfs/
   - Go to https://openstax.org/books/[book-id]
   - Click "Download PDF" button
   - Save to ~/Downloads/openstax_pdfs/[book-id].pdf

2. Run this script to process them

Example books to download:
- American Government 2e: https://openstax.org/books/american-government-2e
- Prealgebra 2e: https://openstax.org/books/prealgebra-2e
- Writing Guide: https://openstax.org/books/writing-guide
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Map book IDs to expected filenames
BOOK_IDS = {
    "american-government-2e": "American Government 2e",
    "prealgebra-2e": "Prealgebra 2e",
    "writing-guide": "Writing Guide with Handbook",
    "preparing-for-college-success": "Preparing for College Success",
    "developmental-math": "Developmental Mathematics",
    "elementary-algebra": "Elementary Algebra",
    "us-history": "U.S. History",
    "world-history": "World History",
    "biology-2e": "Biology 2e",
    "chemistry-2e": "Chemistry 2e",
}


async def process_local_pdf(
    pdf_path: Path,
    book_id: str,
    max_chapters: int = 2
):
    """
    Process a local OpenStax PDF

    Args:
        pdf_path: Path to the downloaded PDF
        book_id: Book identifier
        max_chapters: Maximum chapters to process (for testing)
    """
    from src.services.openstax_toc_extractor import OpenStaxTOCExtractor
    from src.services.openstax_pdf_splitter import OpenStaxPDFSplitter
    from src.services.openstax_content_extractor import OpenStaxContentExtractor

    logger.info("=" * 60)
    logger.info(f"Processing: {pdf_path.name}")
    logger.info(f"Book ID: {book_id}")
    logger.info("=" * 60)

    # Step 1: Extract TOC
    logger.info("\nStep 1: Extracting Table of Contents...")
    toc_extractor = OpenStaxTOCExtractor()

    try:
        toc = toc_extractor.extract_from_pdf(pdf_path)
        logger.info(f"✓ Book Title: {toc.book_title}")
        logger.info(f"✓ Total Pages: {toc.total_pages}")
        logger.info(f"✓ Chapters Found: {len(toc.chapters)}")

        # Show first few chapters
        logger.info("\nFirst 5 chapters:")
        for chapter in toc.chapters[:5]:
            logger.info(f"  Chapter {chapter.chapter_number}: {chapter.title}")
            logger.info(f"    Pages: {chapter.start_page}-{chapter.end_page}")
    except Exception as e:
        logger.error(f"✗ TOC extraction failed: {e}")
        logger.info("\nYou can still proceed with manual chapter boundaries...")
        return None

    # Step 2: Split into chapters
    logger.info("\nStep 2: Splitting PDF into chapters...")
    splitter = OpenStaxPDFSplitter()

    try:
        chapter_pdfs = splitter.split_into_chapters(pdf_path, toc, book_id)
        logger.info(f"✓ Created {len(chapter_pdfs)} chapter PDFs")

        # Limit chapters for testing
        if max_chapters and len(chapter_pdfs) > max_chapters:
            logger.info(f"  (Testing with first {max_chapters} chapters only)")
            chapter_pdfs = chapter_pdfs[:max_chapters]

    except Exception as e:
        logger.error(f"✗ Splitting failed: {e}")
        return None

    # Step 3: Extract content from each chapter
    logger.info("\nStep 3: Extracting structured content...")
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

            # Show sample text (first 200 chars)
            sample_text = content.get_full_text()[:200]
            logger.info(f"  Sample Text: \"{sample_text}...\"")

            logger.info(f"  ✓ Extraction complete")

        except Exception as e:
            logger.error(f"  ✗ Error extracting chapter: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing Complete!")
    logger.info(f"{'='*60}")
    logger.info(f"Output Locations:")
    logger.info(f"  Source PDF: {pdf_path}")
    logger.info(f"  Chapter PDFs: {splitter.output_dir}")
    logger.info(f"  Extracted Images: {extractor.assets_dir}")
    logger.info(f"\nNext Steps:")
    logger.info(f"  1. Review extracted content")
    logger.info(f"  2. Implement LLM chunking")
    logger.info(f"  3. Generate embeddings")
    logger.info(f"  4. Store in vector store")
    logger.info(f"{'='*60}\n")

    return {
        "pdf_path": pdf_path,
        "toc": toc,
        "chapter_pdfs": chapter_pdfs,
    }


async def scan_and_process():
    """Scan the download folder and process all PDFs"""
    download_dir = Path.home() / "Downloads" / "openstax_pdfs"

    logger.info("=" * 60)
    logger.info("Scanning for OpenStax PDFs")
    logger.info("=" * 60)
    logger.info(f"Looking in: {download_dir}")

    if not download_dir.exists():
        logger.error(f"\n❌ Download directory not found: {download_dir}")
        logger.info("\nPlease create it and download PDFs:")
        logger.info(f"  mkdir -p {download_dir}")
        logger.info("\nThen download OpenStax PDFs to that folder:")
        logger.info("  https://openstax.org/books/american-government-2e")
        logger.info("  https://openstax.org/books/prealgebra-2e")
        logger.info("  etc.")
        return

    # Find all PDFs
    pdf_files = list(download_dir.glob("*.pdf"))

    if not pdf_files:
        logger.error(f"\n❌ No PDFs found in: {download_dir}")
        logger.info("\nPlease download some OpenStax PDFs to that folder.")
        return

    logger.info(f"\n✓ Found {len(pdf_files)} PDF(s):")
    for pdf in pdf_files:
        logger.info(f"  - {pdf.name} ({pdf.stat().st_size / (1024*1024):.1f} MB)")

    # Try to identify books by filename
    results = {}
    for pdf_file in pdf_files:
        # Try to match book ID by filename
        book_id = None
        for bid, title in BOOK_IDS.items():
            if bid.lower() in pdf_file.name.lower() or title.lower() in pdf_file.name.lower():
                book_id = bid
                break

        if not book_id:
            # Use filename stem as book_id
            book_id = pdf_file.stem
            logger.warning(f"Unknown book, using ID: {book_id}")

        try:
            result = await process_local_pdf(pdf_file, book_id, max_chapters=2)
            results[book_id] = result
        except Exception as e:
            logger.error(f"\n❌ Failed to process {pdf_file.name}: {e}")
            import traceback
            traceback.print_exc()

    return results


if __name__ == "__main__":
    print("OpenStax Pipeline Test (Local PDFs)")
    print("=" * 60)
    print("This script will process PDFs you've manually downloaded.")
    print()

    results = asyncio.run(scan_and_process())

    if results:
        print("\n✓ Processing complete!")
        print(f"  Successfully processed: {len(results)} book(s)")
    else:
        print("\n⚠ No books were processed.")
