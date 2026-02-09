"""
OpenStax Textbook Downloader - Mu2 Cognitive OS
==============================================

Downloads OpenStax textbook PDFs for processing.

OpenStax books are available under CC BY 4.0 license:
https://openstax.org/license
"""

from pathlib import Path
import logging
import httpx
from typing import Optional
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OpenStaxBook:
    """Represents an OpenStax textbook"""
    book_id: str
    title: str
    subject: str
    pdf_url: str
    web_view_url: str
    grade_level: str  # "middle", "high", "ap"
    florida_standard: Optional[str] = None


# OpenStax textbooks we're using (from our Florida standards analysis)
OPENSTAX_BOOKS = {
    # ELA / College Success
    "writing-guide": OpenStaxBook(
        book_id="writing-guide",
        title="Writing Guide with Handbook",
        subject="English Language Arts",
        pdf_url="https://openstax.org/contents/writing-guide.pdf",
        web_view_url="https://openstax.org/books/writing-guide",
        grade_level="high",
        florida_standard="ELA 6-12"
    ),
    "preparing-for-college-success": OpenStaxBook(
        book_id="preparing-for-college-success",
        title="Preparing for College Success",
        subject="College Success",
        pdf_url="https://openstax.org/contents/preparing-for-college-success.pdf",
        web_view_url="https://openstax.org/books/preparing-for-college-success",
        grade_level="middle-high",
        florida_standard="ELA 6-12"
    ),

    # Mathematics
    "developmental-math": OpenStaxBook(
        book_id="developmental-math",
        title="Developmental Mathematics",
        subject="Mathematics",
        pdf_url="https://openstax.org/contents/developmental-math.pdf",
        web_view_url="https://openstax.org/books/developmental-math",
        grade_level="middle",
        florida_standard="Math 6-7"
    ),
    "prealgebra-2e": OpenStaxBook(
        book_id="prealgebra-2e",
        title="Prealgebra 2e",
        subject="Mathematics",
        pdf_url="https://openstax.org/contents/prealgebra-2e.pdf",
        web_view_url="https://openstax.org/books/prealgebra-2e",
        grade_level="middle",
        florida_standard="Math 6-7"
    ),
    "elementary-algebra": OpenStaxBook(
        book_id="elementary-algebra",
        title="Elementary Algebra",
        subject="Mathematics",
        pdf_url="https://openstax.org/contents/elementary-algebra.pdf",
        web_view_url="https://openstax.org/books/elementary-algebra",
        grade_level="middle-high",
        florida_standard="Math 7-8"
    ),

    # Social Studies (CRITICAL for Civics EOC)
    "american-government-2e": OpenStaxBook(
        book_id="american-government-2e",
        title="American Government 2e",
        subject="Civics",
        pdf_url="https://openstax.org/contents/american-government-2e.pdf",
        web_view_url="https://openstax.org/books/american-government-2e",
        grade_level="high",
        florida_standard="7th Grade Civics EOC ✅"
    ),
    "us-history": OpenStaxBook(
        book_id="us-history",
        title="U.S. History",
        subject="U.S. History",
        pdf_url="https://openstax.org/contents/us-history.pdf",
        web_view_url="https://openstax.org/books/us-history",
        grade_level="high",
        florida_standard="8th Grade + HS US History"
    ),
    "world-history": OpenStaxBook(
        book_id="world-history",
        title="World History",
        subject="World History",
        pdf_url="https://openstax.org/contents/world-history.pdf",
        web_view_url="https://openstax.org/books/world-history",
        grade_level="high",
        florida_standard="6th Grade + HS World History"
    ),

    # Science
    "biology-2e": OpenStaxBook(
        book_id="biology-2e",
        title="Biology 2e",
        subject="Biology",
        pdf_url="https://openstax.org/biology-2e/pdf",  # Note: Different URL pattern
        web_view_url="https://openstax.org/books/biology-2e",
        grade_level="high",
        florida_standard="8th Science + HS Biology"
    ),
    "chemistry-2e": OpenStaxBook(
        book_id="chemistry-2e",
        title="Chemistry 2e",
        subject="Chemistry",
        pdf_url="https://openstax.org/contents/chemistry-2e.pdf",
        web_view_url="https://openstax.org/books/chemistry-2e",
        grade_level="high",
        florida_standard="8th Physical Science + HS Chemistry"
    ),
    "high-school-physics": OpenStaxBook(
        book_id="high-school-physics",
        title="High School Physics",
        subject="Physics",
        pdf_url="https://openstax.org/contents/high-school-physics.pdf",
        web_view_url="https://openstax.org/books/high-school-physics",
        grade_level="high",
        florida_standard="HS Physics"
    ),
}


class OpenStaxDownloader:
    """
    Downloads OpenStax textbook PDFs
    """

    def __init__(self, download_dir: str = "/tmp/openstax_downloads"):
        """
        Initialize downloader

        Args:
            download_dir: Directory to save downloaded PDFs
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def download_pdf(self, book: OpenStaxBook) -> Path:
        """
        Download a single textbook PDF

        Args:
            book: OpenStax book to download

        Returns:
            Path to downloaded PDF
        """
        pdf_path = self.download_dir / f"{book.book_id}.pdf"

        # Check if already downloaded
        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
            logger.info(f"PDF already exists: {pdf_path}")
            return pdf_path

        logger.info(f"Downloading {book.title}...")

        # Try multiple URL patterns (OpenStax changed their URL structure)
        url_patterns = [
            book.pdf_url,  # Primary URL from book metadata
            f"https://openstax.org/books/{book.book_id}/pdf",
            f"https://openstax.org/contents/{book.book_id}.pdf",
            f"https://openstax.org/{book.book_id}/pdf",
        ]

        for url in url_patterns:
            try:
                logger.debug(f"Trying URL: {url}")
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    response = await client.get(url)
                    response.raise_for_status()

                    # Check if we got a PDF (content-type check)
                    content_type = response.headers.get("content-type", "")
                    if "pdf" not in content_type.lower():
                        logger.debug(f"URL didn't return PDF (got {content_type}), trying next...")
                        continue

                    # Save PDF
                    pdf_path.write_bytes(response.content)

                    logger.info(f"Downloaded {book.title} from {url}")
                    logger.info(f"File size: {len(response.content):,} bytes")
                    return pdf_path

            except Exception as e:
                logger.debug(f"Failed to download from {url}: {e}")
                continue

        # If we get here, all URLs failed
        logger.error(f"Error downloading {book.book_id}: All URL patterns failed")
        raise Exception(f"Could not download {book.book_id} from any known URL pattern")

    async def download_all(self, book_ids: list[str] = None) -> dict[str, Path]:
        """
        Download multiple OpenStax textbooks

        Args:
            book_ids: List of book IDs to download (None = all)

        Returns:
            Dict mapping book_id to PDF path
        """
        if book_ids is None:
            book_ids = list(OPENSTAX_BOOKS.keys())

        results = {}

        for book_id in book_ids:
            if book_id not in OPENSTAX_BOOKS:
                logger.warning(f"Unknown book ID: {book_id}")
                continue

            book = OPENSTAX_BOOKS[book_id]
            try:
                pdf_path = await self.download_pdf(book)
                results[book_id] = pdf_path
            except Exception as e:
                logger.error(f"Failed to download {book_id}: {e}")

        return results

    def get_book(self, book_id: str) -> OpenStaxBook:
        """Get book metadata by ID"""
        return OPENSTAX_BOOKS.get(book_id)


# Convenience functions
async def download_openstax_pdf(book_id: str) -> Path:
    """Download a single OpenStax textbook PDF"""
    downloader = OpenStaxDownloader()
    return await downloader.download_pdf(downloader.get_book(book_id))


async def download_openstax_multiple(book_ids: list[str]) -> dict[str, Path]:
    """Download multiple OpenStax textbook PDFs"""
    downloader = OpenStaxDownloader()
    return await downloader.download_all(book_ids)


if __name__ == "__main__":
    # Test download
    import asyncio

    async def test_download():
        downloader = OpenStaxDownloader()

        # Test with a smaller book first
        print("Testing download with American Government 2e...")
        path = await downloader.download_pdf(OPENSTAX_BOOKS["american-government-2e"])
        print(f"Downloaded to: {path}")
        print(f"File size: {path.stat().st_size:,} bytes")

    asyncio.run(test_download())
