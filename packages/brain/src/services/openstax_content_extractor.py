"""
OpenStax Content Extractor - Mu2 Cognitive OS
==========================================

Extracts structured content from OpenStax chapter PDFs.

Handles:
- Text extraction with layout preservation
- Image extraction
- Table parsing
- Metadata generation
"""

from pathlib import Path
import logging
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
import json
import re

# Import Any for type checking only
if TYPE_CHECKING:
    from .openstax_pdf_splitter import Any

logger = logging.getLogger(__name__)


@dataclass
class ExtractedImage:
    """An image extracted from a chapter"""
    image_id: str
    chapter_id: str
    page_number: int
    image_index: int
    file_path: Path
    caption: Optional[str] = None
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x0, y0, x1, y1)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedTable:
    """A table extracted from a chapter"""
    table_id: str
    chapter_id: str
    page_number: int
    table_index: int
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None
    markdown: str = ""  # Markdown representation
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Section:
    """A section within a chapter"""
    section_id: str
    chapter_id: str
    title: str
    level: int  # 1 = h1, 2 = h2, etc.
    page_number: int
    content: str
    subsections: List['Section'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChapterContent:
    """Full content extracted from a chapter"""
    chapter_id: str
    book_id: str
    chapter_number: int
    title: str
    authors: List[str] = field(default_factory=list)
    text_content: str = ""
    sections: List[Section] = field(default_factory=list)
    images: List[ExtractedImage] = field(default_factory=list)
    tables: List[ExtractedTable] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_full_text(self) -> str:
        """Get all text content in order"""
        text = self.text_content or ""

        # Add section content
        for section in self.sections:
            text += f"\n\n{section.title}\n{section.content}"

            for subsection in section.subsections:
                text += f"\n\n{subsection.title}\n{subsection.content}"

        return text


class OpenStaxContentExtractor:
    """
    Extracts structured content from OpenStax chapter PDFs

    Uses pdfplumber for text extraction with layout preservation.
    """

    def __init__(self, assets_dir: str = "/tmp/openstax_assets"):
        """
        Initialize extractor

        Args:
            assets_dir: Directory to save extracted images
        """
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def extract_chapter_content(
        self,
        chapter_pdf: Any,  # Any object from openstax_pdf_splitter
        book_id: str
    ) -> ChapterContent:
        """
        Extract all content from a chapter PDF

        Args:
            chapter_pdf: Chapter PDF to process
            book_id: Book identifier

        Returns:
            Structured chapter content
        """
        logger.info(f"Extracting content from {chapter_pdf.pdf_path.name}")

        try:
            import pypdf
            import pdfplumber

            chapter_id = f"{book_id}_chapter{chapter_pdf.chapter_number:02d}"

            with pdfplumber.open(str(chapter_pdf.pdf_path)) as pdf:
                # Extract text with layout
                text_content = self._extract_text_with_layout(pdf, chapter_pdf)

                # Extract images
                images = self._extract_images(pdf, chapter_pdf, chapter_id)

                # Extract tables
                tables = self._extract_tables(pdf, chapter_pdf, chapter_id)

                # Parse sections
                sections = self._parse_sections(pdf, chapter_pdf, chapter_id)

                # Get metadata
                metadata = self._extract_metadata(pdf, chapter_pdf, book_id)

            content = ChapterContent(
                chapter_id=chapter_id,
                book_id=book_id,
                chapter_number=chapter_pdf.chapter_number,
                title=chapter_pdf.title,
                text_content=text_content,
                sections=sections,
                images=images,
                tables=tables,
                metadata=metadata
            )

            logger.info(f"Extracted {len(content.sections)} sections, {len(content.images)} images, {len(content.tables)} tables")
            return content

        except Exception as e:
            logger.error(f"Error extracting content from {chapter_pdf.pdf_path}: {e}")
            raise

    def _extract_text_with_layout(self, pdf, chapter_pdf: Any) -> str:
        """Extract text preserving layout structure"""
        import pdfplumber

        text_parts = []

        # For chapter PDFs, pages start from 0
        # The chapter PDF contains pages from start_page to end_page of the original
        # So we just extract all pages from the chapter PDF
        for page in pdf.pages:
            try:
                # Extract text using pdfplumber's extract_text()
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            except Exception as e:
                logger.debug(f"Could not extract text from page: {e}")

        return "\n\n".join(text_parts)

    def _extract_images(
        self,
        pdf,
        chapter_pdf: Any,
        chapter_id: str
    ) -> List[ExtractedImage]:
        """Extract images from chapter PDF"""
        images = []

        try:
            import io

            # Chapter PDFs are self-contained - just iterate all pages
            for page_num, page in enumerate(pdf.pages):
                try:
                    # pdfplumber's .images property
                    if hasattr(page, 'images'):
                        for image_obj in page.images:
                            try:
                                # Get image data from within page
                                image_stream = image_obj.get_stream()
                                image_bytes = image_stream.get_data()

                                # Save image
                                image_filename = f"{chapter_id}_page{page_num+1}_{len(images)+1}.png"
                                image_path = self.assets_dir / image_filename

                                with open(image_path, "wb") as img_file:
                                    img_file.write(image_bytes)

                                # Get bounding box if available
                                bbox = None
                                if hasattr(image_obj, "bbox"):
                                    bbox = (
                                        image_obj.bbox.x0,
                                        image_obj.bbox.y0,
                                        image_obj.bbox.x1,
                                        image_obj.bbox.y1
                                    )

                                image = ExtractedImage(
                                    image_id=f"{chapter_id}_{len(images)+1}",
                                    chapter_id=chapter_id,
                                    page_number=page_num + 1,
                                    image_index=len(images) + 1,
                                    file_path=image_path,
                                    bbox=bbox
                                )
                                images.append(image)

                            except Exception as e:
                                logger.debug(f"Could not extract image: {e}")

                except Exception as e:
                    logger.debug(f"Error processing page {page_num}: {e}")

        except Exception as e:
            logger.warning(f"Error extracting images: {e}")

        return images

    def _extract_tables(
        self,
        pdf,
        chapter_pdf: Any,
        chapter_id: str
    ) -> List[ExtractedTable]:
        """Extract tables from chapter PDF"""
        tables = []

        try:
            import pdfplumber

            # Chapter PDFs are self-contained - iterate all pages
            for page_num, page in enumerate(pdf.pages):
                try:
                    # Find tables using pdfplumber
                    tables_found = page.find_tables()

                    for table_num, table in enumerate(tables_found):
                        try:
                            # Extract table data
                            table_data = table.extract()

                            if not table_data or len(table_data) == 0:
                                continue

                            # First row is headers
                            headers = table_data[0]
                            rows = table_data[1:] if len(table_data) > 1 else []

                            # Generate simple markdown
                            markdown_lines = []
                            if headers:
                                markdown_lines.append("| " + " | ".join(str(h) for h in headers) + " |")
                                markdown_lines.append("|" + "|".join(["---"] * len(headers)) + "|")
                            for row in rows:
                                markdown_lines.append("| " + " | ".join(str(c) for c in row) + " |")
                            markdown = "\n".join(markdown_lines)

                            table = ExtractedTable(
                                table_id=f"{chapter_id}_table{len(tables)+1}",
                                chapter_id=chapter_id,
                                page_number=page_num + 1,
                                table_index=table_num + 1,
                                headers=[str(h) for h in headers],
                                rows=[[str(c) for c in row] for row in rows],
                                markdown=markdown
                            )
                            tables.append(table)

                        except Exception as e:
                            logger.debug(f"Could not extract table {table_num}: {e}")

                except Exception as e:
                    logger.debug(f"Error processing page {page_num}: {e}")

        except Exception as e:
            logger.warning(f"Error extracting tables: {e}")

        return tables

    def _parse_sections(
        self,
        pdf,
        chapter_pdf: Any,
        chapter_id: str
    ) -> List[Section]:
        """Parse section headings from chapter content"""
        sections = []

        try:
            import pdfplumber

            current_section = None

            # Chapter PDFs are self-contained - iterate all pages
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()

                if not text:
                    continue

                # Look for section headings (simplified pattern matching)
                # OpenStax typically uses: "1.1 Section Title", "Key Terms", etc.
                lines = text.split("\n")

                for line in lines:
                    line = line.strip()

                    # Check for heading patterns
                    if re.match(r"^\d+\.\d+\s+\S+", line):  # e.g., "1.1 Introduction"
                        level = 2  # h2 equivalent
                        title = line
                        current_section = Section(
                            section_id=f"{chapter_id}_section_{len(sections)+1}",
                            chapter_id=chapter_id,
                            title=title,
                            level=level,
                            page_number=page_num + 1,
                            content="",
                            subsections=[]
                        )
                        sections.append(current_section)

                    elif re.match(r"^\d+\s+[A-Z][A-Z\s]+$", line):  # ALL CAPS heading
                        level = 2
                        title = line
                        current_section = Section(
                            section_id=f"{chapter_id}_section_{len(sections)+1}",
                            chapter_id=chapter_id,
                            title=title,
                            level=level,
                            page_number=page_num + 1,
                            content="",
                            subsections=[]
                        )
                        sections.append(current_section)

        except Exception as e:
            logger.warning(f"Error parsing sections: {e}")

        return sections

    def _extract_metadata(
        self,
        pdf,
        chapter_pdf: Any,
        book_id: str
    ) -> Dict[str, Any]:
        """Extract metadata from chapter PDF"""
        import pypdf

        metadata = {
            "book_id": book_id,
            "chapter_number": chapter_pdf.chapter_number,
            "title": chapter_pdf.title,
            "file_path": str(chapter_pdf.pdf_path),
            "file_size": chapter_pdf.file_size,
            "page_range": chapter_pdf.page_range,
            "extraction_date": datetime.utcnow().isoformat(),
            "total_pages": chapter_pdf.page_range[1] - chapter_pdf.page_range[0] + 1
        }

        # Try to get PDF metadata
        try:
            pdf_reader = pypdf.PdfReader(str(chapter_pdf.pdf_path))
            if "/Title" in pdf_reader.metadata:
                metadata["book_title"] = pdf_reader.metadata["/Title"]
            if "/Authors" in pdf_reader.metadata:
                metadata["authors"] = pdf_reader.metadata["/Authors"]
        except:
            pass

        return metadata

    def extract_all_chapters(
        self,
        chapter_pdfs: List[Any],
        book_id: str
    ) -> List[ChapterContent]:
        """
        Extract content from all chapter PDFs

        Args:
            chapter_pdfs: List of chapter PDFs
            book_id: Book identifier

        Returns:
            List of chapter content objects
        """
        contents = []

        for chapter_pdf in chapter_pdfs:
            try:
                content = self.extract_chapter_content(chapter_pdf, book_id)
                contents.append(content)
            except Exception as e:
                logger.error(f"Error extracting from {chapter_pdf.pdf_path.name}: {e}")
                continue

        logger.info(f"Extracted content from {len(contents)} chapters")
        return contents


# Convenience functions
def extract_chapter_content(chapter_pdf: Any, book_id: str) -> ChapterContent:
    """Extract content from a single chapter PDF"""
    extractor = OpenStaxContentExtractor()
    return extractor.extract_chapter_content(chapter_pdf, book_id)


if __name__ == "__main__":
    # Test extraction
    import asyncio
    from services.openstax_pdf_splitter import Any
    from services.openstax_downloader import OpenStaxDownloader, OPENSTAX_BOOKS

    async def test_extraction():
        # Download, split, and extract
        downloader = OpenStaxDownloader()

        # Download PDF (use small book for testing)
        pdf_path = await downloader.download_pdf(OPENSTAX_BOOKS["prealgebra"])

        # Create a test Any
        chapter_pdf = Any(
            chapter_number=1,
            title="Whole Numbers",
            pdf_path=pdf_path,
            page_range=(1, 50),
            file_size=pdf_path.stat().st_size
        )

        # Extract content
        extractor = OpenStaxContentExtractor()
        content = extractor.extract_chapter_content(chapter_pdf, "prealgebra")

        print(f"Chapter: {content.title}")
        print(f"Text length: {len(content.text_content)} characters")
        print(f"Sections: {len(content.sections)}")
        print(f"Images: {len(content.images)}")
        print(f"Tables: {len(content.tables)}")

    asyncio.run(test_extraction())
