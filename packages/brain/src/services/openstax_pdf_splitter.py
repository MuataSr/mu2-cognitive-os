"""
OpenStax PDF Chapter Splitter - Mu2 Cognitive OS
==========================================

Splits large OpenStax textbook PDFs into individual chapter PDFs
for easier processing and chunking.

Uses PyPDF2 to create separate PDF files for each chapter.
"""

from pathlib import Path
import logging
from typing import List, Dict, Optional, TYPE_CHECKING, Any
from dataclasses import dataclass
from pypdf import PdfReader, PdfWriter
import shutil
import re

# Import Chapter for type checking, but avoid circular import at runtime
if TYPE_CHECKING:
    from .openstax_toc_extractor import Chapter, TOC

logger = logging.getLogger(__name__)


@dataclass
class ChapterPDF:
    """Represents a single chapter PDF"""
    chapter_number: int
    title: str
    pdf_path: Path
    page_range: tuple[int, int]  # (start, end)
    file_size: int


class OpenStaxPDFSplitter:
    """
    Splits OpenStax textbook PDFs into chapter PDFs
    """

    def __init__(self, output_dir: str = "/tmp/openstax_chapters"):
        """
        Initialize splitter

        Args:
            output_dir: Directory to save chapter PDFs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def split_into_chapters(
        self,
        pdf_path: Path,
        toc: Any,  # TOC object from openstax_toc_extractor
        book_id: str
    ) -> List[ChapterPDF]:
        """
        Split PDF into individual chapter PDFs

        Args:
            pdf_path: Path to source PDF
            toc: Table of contents with chapter boundaries
            book_id: Book identifier

        Returns:
            List of chapter PDFs with metadata
        """
        logger.info(f"Splitting {pdf_path.name} into chapters...")

        try:
            pdf_reader = PdfReader(str(pdf_path))
            chapter_pdfs = []

            for chapter in toc.chapters:
                # Create new PDF for this chapter
                pdf_writer = PdfWriter()

                # Add pages from start_page to end_page
                start_page = chapter.start_page - 1  # Convert to 0-indexed
                end_page = chapter.end_page if chapter.end_page else len(pdf_reader.pages)

                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])

                # Save chapter PDF
                safe_title = self._sanitize_filename(chapter.title)
                chapter_filename = f"{book_id}_chapter{chapter.chapter_number:02d}_{safe_title}.pdf"
                chapter_path = self.output_dir / chapter_filename

                with open(chapter_path, "wb") as output_file:
                    pdf_writer.write(output_file)

                chapter_pdf = ChapterPDF(
                    chapter_number=chapter.chapter_number,
                    title=chapter.title,
                    pdf_path=chapter_path,
                    page_range=(chapter.start_page, chapter.end_page or toc.total_pages),
                    file_size=chapter_path.stat().st_size
                )

                chapter_pdfs.append(chapter_pdf)

                logger.info(f"Created: {chapter_filename} ({chapter_pdf.file_size:,} bytes, pages {chapter_pdf.page_range})")

            logger.info(f"Split into {len(chapter_pdfs)} chapters")
            return chapter_pdfs

        except Exception as e:
            logger.error(f"Error splitting PDF: {e}")
            raise

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename"""
        # Remove special characters, replace spaces with underscores
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        # Limit length
        return sanitized[:50]  # Max 50 characters

    def split_all_chapters(
        self,
        pdf_path: Path,
        chapters: List[Any],  # List of Chapter objects from openstax_toc_extractor
        book_id: str
    ) -> List[ChapterPDF]:
        """
        Split PDF using simple chapter list (without TOC object)

        Args:
            pdf_path: Path to source PDF
            chapters: List of Chapter objects
            book_id: Book identifier

        Returns:
            List of chapter PDFs
        """
        logger.info(f"Splitting {pdf_path.name} into {len(chapters)} chapters...")

        try:
            pdf_reader = PdfReader(str(pdf_path))
            chapter_pdfs = []

            for i, chapter in enumerate(chapters):
                # Create new PDF for this chapter
                pdf_writer = PdfWriter()

                # Add pages from start_page to end_page
                start_page = chapter.start_page - 1  # Convert to 0-indexed
                end_page = chapter.end_page if chapter.end_page else (i + 1 < len(chapters) and chapters[i + 1].start_page - 1)

                if not end_page:
                    end_page = len(pdf_reader.pages)

                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])

                # Save chapter PDF
                safe_title = self._sanitize_filename(chapter.title)
                chapter_filename = f"{book_id}_chapter{i+1:02d}_{safe_title}.pdf"
                chapter_path = self.output_dir / chapter_filename

                with open(chapter_path, "wb") as output_file:
                    pdf_writer.write(output_file)

                chapter_pdf = ChapterPDF(
                    chapter_number=i + 1,
                    title=chapter.title,
                    pdf_path=chapter_path,
                    page_range=(chapter.start_page, end_page or len(pdf_reader.pages)),
                    file_size=chapter_path.stat().st_size
                )

                chapter_pdfs.append(chapter_pdf)

                logger.info(f"Created: {chapter_filename} (pages {chapter_pdf.page_range})")

            logger.info(f"Split into {len(chapter_pdfs)} chapters")
            return chapter_pdfs

        except Exception as e:
            logger.error(f"Error splitting PDF: {e}")
            raise


# Convenience functions
def split_pdf_into_chapters(
    pdf_path: str,
    chapters: List[Any],  # List of Chapter objects from openstax_toc_extractor
    book_id: str,
    output_dir: str = "/tmp/openstax_chapters"
) -> List[ChapterPDF]:
    """Split a PDF into chapter PDFs"""
    splitter = OpenStaxPDFSplitter(output_dir)
    return splitter.split_all_chapters(Path(pdf_path), chapters, book_id)


if __name__ == "__main__":
    # Test splitting
    import asyncio
    from services.openstax_toc_extractor import OpenStaxTOCExtractor, Chapter
    from services.openstax_downloader import OpenStaxDownloader, OPENSTAX_BOOKS

    async def test_split():
        # Download and split a PDF
        downloader = OpenStaxDownloader()
        toc_extractor = OpenStaxTOCExtractor()

        # Download PDF
        pdf_path = await downloader.download_pdf(OPENSTAX_BOOKS["american-government-2e"])

        # Extract TOC
        toc = toc_extractor.extract_from_pdf(pdf_path)

        # Split into chapters
        splitter = OpenStaxPDFSplitter()
        chapter_pdfs = splitter.split_into_chapters(pdf_path, toc, "american-government-2e")

        print(f"\nCreated {len(chapter_pdfs)} chapter PDFs:")
        for cp in chapter_pdfs:
            print(f"  - {cp.pdf_path.name}")

    asyncio.run(test_split())
