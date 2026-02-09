"""
OpenStax PDF TOC Extractor - Mu2 Cognitive OS
============================================

Extracts table of contents from OpenStax PDFs and identifies chapter boundaries.

Uses pdfplumber to parse PDF structure and identify chapter/page boundaries.
"""

from pathlib import Path
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    """Represents a chapter in the textbook"""
    chapter_number: int
    title: str
    start_page: int
    end_page: Optional[int] = None
    level: int = 1  # 1 = top level, 2 = subsection
    parent_chapter: Optional[int] = None


@dataclass
class TOC:
    """Table of contents for a textbook"""
    book_id: str
    book_title: str
    chapters: List[Chapter]
    total_pages: int


class OpenStaxTOCExtractor:
    """
    Extracts table of contents from OpenStax PDFs

    Strategy:
    1. Use pdfplumber to parse PDF structure
    2. Look for chapter headings in document outline
    3. Fallback: Search for chapter patterns ("Chapter X")
    4. Identify page ranges for each chapter
    """

    # Patterns for chapter headings (OpenStax typically uses these formats)
    CHAPTER_PATTERNS = [
        r"^Chapter\s+(\d+)[\s:]+(.+)",  # "Chapter 1: The American Revolution"
        r"^Chapter\s+(\d+)$",  # "Chapter 1" alone
        r"^Part\s+[IVX]+[\s:]+(.+)",  # "Part I: Foundations"
        r"^Section\s+(\d+)[\s:]+(.+)",  # "Section 1.1: Introduction"
        r"^(Appendix|Glossary|Index|References)[\s:]*",  # End matter
    ]

    def __init__(self):
        self.logger = logger

    def extract_from_pdf(self, pdf_path: Path) -> TOC:
        """
        Extract TOC from PDF

        Args:
            pdf_path: Path to PDF file

        Returns:
            Table of contents with chapter boundaries
        """
        import pypdf

        self.logger.info(f"Extracting TOC from {pdf_path.name}")

        try:
            # Open PDF
            pdf_reader = pypdf.PdfReader(pdf_path)
            total_pages = len(pdf_reader.pages)

            # Get document outline (if available)
            outline = pdf_reader.outline

            chapters = []

            if outline:
                # Use PDF outline (most reliable)
                chapters.extend(self._parse_outline(outline, pdf_reader))
            else:
                # Fallback: Search for chapter headings in text
                chapters = self._extract_chapters_from_text(pdf_reader)

            # Calculate end pages
            self._calculate_end_pages(chapters, total_pages)

            # Get book title
            book_title = self._extract_title(pdf_reader)

            toc = TOC(
                book_id=pdf_path.stem,
                book_title=book_title,
                chapters=chapters,
                total_pages=total_pages
            )

            self.logger.info(f"Found {len(chapters)} chapters in {book_title}")
            return toc

        except Exception as e:
            self.logger.error(f"Error extracting TOC from {pdf_path}: {e}")
            raise

    def _parse_outline(self, outline: list, pdf_reader) -> List[Chapter]:
        """Parse PDF outline structure for OpenStax textbooks"""
        chapters = []

        def parse_outline_level(outline, level=0):
            """Recursively parse outline levels"""
            for item in outline:
                # Handle OpenStax outline format (dict with /Title and /Page)
                if isinstance(item, dict):
                    title = item.get("/Title", "")
                    page_ref = item.get("/Page", None)

                    # Extract chapter number from title
                    chapter_num = self._extract_chapter_number(title)

                    # Check if this is a chapter heading
                    if self._is_chapter_heading(title, level) and chapter_num:
                        # Get page number from IndirectObject
                        page_num = self._resolve_page_number(page_ref, pdf_reader)

                        chapter = Chapter(
                            chapter_number=chapter_num,
                            title=title.strip(),
                            start_page=page_num,
                            level=level,
                            parent_chapter=None
                        )
                        chapters.append(chapter)

                # Handle nested outline items (list of subsections)
                elif isinstance(item, list):
                    parse_outline_level(item, level + 1)

                # Handle tuple format (some PDFs use this)
                elif isinstance(item, tuple) and len(item) >= 2:
                    title = item[0] if isinstance(item[0], str) else ""
                    children = item[1] if len(item) > 1 else []

                    if self._is_chapter_heading(title, level):
                        chapter_num = self._extract_chapter_number(title)
                        if chapter_num:
                            chapter = Chapter(
                                chapter_number=chapter_num,
                                title=title.strip(),
                                start_page=None,
                                level=level,
                                parent_chapter=None
                            )
                            chapters.append(chapter)

                    # Recurse into children
                    if isinstance(children, list):
                        parse_outline_level(children, level + 1)

        parse_outline_level(outline)
        return chapters

    def _resolve_page_number(self, page_ref, pdf_reader) -> Optional[int]:
        """
        Resolve page number from IndirectObject reference

        Args:
            page_ref: Page reference from outline (IndirectObject pointing to a page dict)
            pdf_reader: PdfReader object

        Returns:
            Page number (1-indexed) or None
        """
        if page_ref is None:
            return None

        try:
            # pypdf stores pages with IndirectObject IDs that can be compared
            # Get the object ID from the reference
            if hasattr(page_ref, 'identifier'):
                ref_id = (page_ref.identifier, page_ref.generation)

                # Find the page with matching object ID
                for i, page in enumerate(pdf_reader.pages):
                    page_dict = page.get_object()
                    if (hasattr(page_dict, 'identifier') and
                        (page_dict.identifier, page_dict.generation) == ref_id):
                        return i + 1  # Convert to 1-indexed

            # Alternative: Compare the actual page objects
            if hasattr(page_ref, 'get_object'):
                page_obj = page_ref.get_object()

                # Compare by object identity (IndirectObjects with same ID are equal)
                for i, page in enumerate(pdf_reader.pages):
                    page_dict = page.get_object()
                    if page_dict == page_obj:
                        return i + 1  # Convert to 1-indexed

        except Exception as e:
            self.logger.debug(f"Could not resolve page number: {e}")

        return None

    def _extract_chapters_from_text(self, pdf_reader) -> List[Chapter]:
        """Extract chapters by searching text content"""
        chapters = []
        current_chapter = 0
        current_page = 0

        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()

            # Search for chapter headings
            for pattern in self.CHAPTER_PATTERNS:
                matches = re.finditer(pattern, text, re.MULTILINE)
                for match in matches:
                    chapter_num_str = match.group(1) if match.lastindex >= 1 else None
                    title = match.group(2) if match.lastindex >= 2 else match.group(0)

                    if chapter_num_str:
                        chapter_num = int(chapter_num_str)
                    else:
                        current_chapter += 1
                        chapter_num = current_chapter

                    chapter = Chapter(
                        chapter_number=chapter_num,
                        title=title.strip(),
                        start_page=page_num + 1  # PDF pages are 0-indexed
                    )
                    chapters.append(chapter)

        return chapters

    def _extract_chapter_number(self, title: str) -> Optional[int]:
        """Extract chapter number from title"""
        match = re.search(r"\b(\d+)\b", title)
        if match:
            return int(match.group(1))
        return None

    def _is_chapter_heading(self, title: str, level: int) -> bool:
        """Determine if a title is a chapter heading"""
        if not title:
            return False

        # Lower priority for Appendix, Glossary, Index, etc.
        lower_title = title.lower().strip()
        skip_words = ["appendix", "glossary", "index", "references", "bibliography",
                      "contents", "preface", "introduction"]
        if any(word in lower_title for word in skip_words):
            return False

        # Check for chapter keywords
        chapter_keywords = ["chapter", "ch "]
        if any(keyword in lower_title for keyword in chapter_keywords):
            return True

        # OpenStax format: "Chapter 1 Whole Numbers"
        if re.match(r'^chapter\s+\d+', lower_title):
            return True

        # OpenStax format: "1.1 Introduction to Whole Numbers" (section, not chapter)
        if re.match(r'^\d+\.\d+', title):
            return False  # These are sections, not chapters

        # Chapter review features
        if "chapter review" in lower_title:
            return False

        return False
        if any(word in lower_title for word in skip_words):
            return False

        # Check for chapter/part/section keywords
        chapter_keywords = ["chapter", "part", "unit"]
        return any(keyword in lower_title for keyword in chapter_keywords)

    def _get_page_number(self, children: list, pdf_reader) -> Optional[int]:
        """Extract page number from child elements"""
        # This would need to implement PDF destination parsing
        # For now, return None
        return None

    def _calculate_end_pages(self, chapters: List[Chapter], total_pages: int):
        """Calculate end page for each chapter"""
        for i, chapter in enumerate(chapters):
            if i < len(chapters) - 1:
                # End page is start of next chapter - 1
                next_start = chapters[i + 1].start_page
                if next_start is not None and next_start > 1:
                    chapter.end_page = next_start - 1
                else:
                    chapter.end_page = None
            else:
                # Last chapter goes to end
                chapter.end_page = total_pages

    def _extract_title(self, pdf_reader) -> str:
        """Extract book title from PDF metadata"""
        # Try metadata
        if "/Title" in pdf_reader.metadata:
            return pdf_reader.metadata["/Title"]

        # Fallback: Try first page text
        try:
            first_page = pdf_reader.pages[0]
            text = first_page.extract_text()[:500]  # First 500 chars
            # Look for title patterns
            lines = text.split("\n")
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if len(line) > 10 and len(line) < 100:
                    # Could be a title
                    return line
        except:
            pass

        return "Unknown Title"


# Convenience functions
def extract_toc_from_pdf(pdf_path: str) -> TOC:
    """Extract TOC from a PDF file"""
    extractor = OpenStaxTOCExtractor()
    return extractor.extract_from_pdf(Path(pdf_path))


if __name__ == "__main__":
    # Test TOC extraction
    import asyncio
    from services.openstax_downloader import OpenStaxDownloader, OPENSTAX_BOOKS

    async def test_extraction():
        downloader = OpenStaxDownloader()
        toc_extractor = OpenStaxTOCExtractor()

        # Download a PDF first
        pdf_path = await downloader.download_pdf(OPENSTAX_BOOKS["american-government-2e"])

        # Extract TOC
        toc = toc_extractor.extract_from_pdf(pdf_path)

        print(f"Book: {toc.book_title}")
        print(f"Total pages: {toc.total_pages}")
        print(f"\nChapters found: {len(toc.chapters)}\n")

        for chapter in toc.chapters[:10]:  # First 10 chapters
            print(f"Chapter {chapter.chapter_number}: {chapter.title}")
            print(f"  Pages: {chapter.start_page}-{chapter.end_page}")
            print()

    asyncio.run(test_extraction())
