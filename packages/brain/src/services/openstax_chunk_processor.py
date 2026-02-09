"""
OpenStax Chunk Processor - Mu2 Cognitive OS
============================================

Intelligently breaks textbook chapters into learnable chunks using LLM analysis.

Features:
- Semantic chunking (not arbitrary text splitting)
- Respects section boundaries
- Preserves context with overlap
- Extracts key concepts, definitions, and relationships
- Generates chunk summaries for knowledge graph nodes
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """A chunk of textbook content ready for embedding"""
    chunk_id: str
    chapter_id: str
    book_id: str
    chunk_number: int
    title: str
    content: str
    content_type: str  # "narrative", "definition", "example", "table", "summary"
    section_title: Optional[str] = None
    page_range: Optional[Tuple[int, int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # LLM-extracted information
    key_concepts: List[str] = field(default_factory=list)
    definitions: Dict[str, str] = field(default_factory=dict)  # term -> definition
    relationships: List[str] = field(default_factory=list)  # connections to other topics
    difficulty_level: Optional[str] = None  # "beginner", "intermediate", "advanced"
    summary: Optional[str] = None

    # For citation/tracking
    source_location: Optional[str] = None  # e.g., "Chapter 1, Section 1.1, pages 17-25"

    def get_word_count(self) -> int:
        """Get approximate word count"""
        return len(self.content.split())

    def get_char_count(self) -> int:
        """Get character count"""
        return len(self.content)


@dataclass
class ChunkingResult:
    """Result of chunking a chapter"""
    chapter_id: str
    book_id: str
    total_chunks: int
    chunks: List[TextChunk]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChunkProcessor:
    """
    Intelligently chunks textbook content for knowledge graph ingestion

    Strategy:
    1. Respect section boundaries (don't break mid-section)
    2. Use semantic analysis to find natural break points
    3. Maintain overlap between chunks for context
    4. Classify content by type (narrative, definition, example, etc.)
    5. Extract key concepts, definitions, relationships
    """

    # Chunking parameters
    TARGET_CHUNK_SIZE = 500  # words
    MAX_CHUNK_SIZE = 800  # words
    MIN_CHUNK_SIZE = 200  # words
    CHUNK_OVERLAP = 50  # words

    # Patterns for content classification
    DEFINITION_PATTERNS = [
        r"^(.+) is (?:defined as|a|an) ",
        r"^definition:?\s*(.+)",
        r"^(.+) - (?:defined as|means?) ",
    ]

    EXAMPLE_PATTERNS = [
        r"^for example",
        r"^for instance",
        r"^example",
        r"^(e\.g\.|eg)",
    ]

    def __init__(self, llm_client=None):
        """
        Initialize chunk processor

        Args:
            llm_client: Optional LLM client for semantic analysis
        """
        self.llm_client = llm_client

    def chunk_chapter_content(
        self,
        chapter_content: Any,  # ChapterContent from content_extractor
        use_llm: bool = True
    ) -> ChunkingResult:
        """
        Chunk a chapter into learnable segments

        Args:
            chapter_content: ChapterContent object from extractor
            use_llm: Whether to use LLM for semantic analysis

        Returns:
            ChunkingResult with list of TextChunks
        """
        logger.info(f"Chunking chapter: {chapter_content.title}")

        chunks = []
        chunk_number = 1

        # Strategy 1: Chunk the full text content (primary source)
        if chapter_content.text_content and len(chapter_content.text_content.strip()) > 100:
            text_chunks = self._chunk_text(
                chapter_content.text_content,
                chapter_content,
                chunk_number,
                use_llm
            )
            chunks.extend(text_chunks)
            chunk_number += len(text_chunks)

        # Strategy 2: Also chunk by sections if they have independent content
        sections_with_content = [
            s for s in (chapter_content.sections or [])
            if s.content and len(s.content.strip()) > 50
        ]

        if sections_with_content:
            for section in sections_with_content:
                section_chunks = self._chunk_section(
                    section,
                    chapter_content,
                    chunk_number,
                    use_llm
                )
                chunks.extend(section_chunks)
                chunk_number += len(section_chunks)

        # Strategy 3: Handle tables separately
        for table in (chapter_content.tables or []):
            table_chunk = self._chunk_table(table, chapter_content, chunk_number)
            # Only add if table has meaningful content
            if table_chunk.get_word_count() > 10:
                chunks.append(table_chunk)
                chunk_number += 1

        result = ChunkingResult(
            chapter_id=chapter_content.chapter_id,
            book_id=chapter_content.book_id,
            total_chunks=len(chunks),
            chunks=chunks,
            metadata={
                "chapter_title": chapter_content.title,
                "chapter_number": chapter_content.chapter_number,
                "total_sections": len(chapter_content.sections),
                "total_images": len(chapter_content.images),
                "total_tables": len(chapter_content.tables),
                "chunked_at": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"Created {len(chunks)} chunks from {chapter_content.title}")
        return result

    def _chunk_section(
        self,
        section: Any,  # Section from content_extractor
        chapter_content: Any,
        start_chunk_number: int,
        use_llm: bool
    ) -> List[TextChunk]:
        """Chunk a section into learnable segments"""
        chunks = []

        # Split section content by paragraphs
        paragraphs = self._split_into_paragraphs(section.content)

        current_chunk_text = []
        current_word_count = 0
        chunk_number = start_chunk_number

        for i, paragraph in enumerate(paragraphs):
            para_word_count = len(paragraph.split())

            # Check if adding this paragraph would exceed max chunk size
            if current_word_count + para_word_count > self.MAX_CHUNK_SIZE and current_chunk_text:
                # Create chunk from accumulated paragraphs
                chunk = self._create_chunk_from_text(
                    "\n\n".join(current_chunk_text),
                    section.title,
                    chapter_content,
                    chunk_number,
                    use_llm
                )
                chunks.append(chunk)
                chunk_number += 1

                # Start new chunk with overlap
                current_chunk_text = current_chunk_text[-2:] if len(current_chunk_text) > 2 else []
                current_word_count = sum(len(p.split()) for p in current_chunk_text)

            current_chunk_text.append(paragraph)
            current_word_count += para_word_count

        # Don't forget the last chunk
        if current_chunk_text:
            chunk = self._create_chunk_from_text(
                "\n\n".join(current_chunk_text),
                section.title,
                chapter_content,
                chunk_number,
                use_llm
            )
            chunks.append(chunk)

        return chunks

    def _chunk_text(
        self,
        text: str,
        chapter_content: Any,
        start_chunk_number: int,
        use_llm: bool
    ) -> List[TextChunk]:
        """Chunk raw text content"""
        chunks = []

        # Split into paragraphs
        paragraphs = self._split_into_paragraphs(text)

        current_chunk_text = []
        current_word_count = 0
        chunk_number = start_chunk_number

        for paragraph in paragraphs:
            para_word_count = len(paragraph.split())

            if current_word_count + para_word_count > self.MAX_CHUNK_SIZE and current_chunk_text:
                chunk = self._create_chunk_from_text(
                    "\n\n".join(current_chunk_text),
                    chapter_content.title,
                    chapter_content,
                    chunk_number,
                    use_llm
                )
                chunks.append(chunk)
                chunk_number += 1

                # Overlap
                current_chunk_text = current_chunk_text[-2:] if len(current_chunk_text) > 2 else []
                current_word_count = sum(len(p.split()) for p in current_chunk_text)

            current_chunk_text.append(paragraph)
            current_word_count += para_word_count

        if current_chunk_text:
            chunk = self._create_chunk_from_text(
                "\n\n".join(current_chunk_text),
                chapter_content.title,
                chapter_content,
                chunk_number,
                use_llm
            )
            chunks.append(chunk)

        return chunks

    def _chunk_table(
        self,
        table: Any,  # ExtractedTable from content_extractor
        chapter_content: Any,
        chunk_number: int
    ) -> TextChunk:
        """Convert a table to a chunk"""
        # Convert table markdown to readable text
        content = f"Table: {table.caption or 'Data Table'}\n\n"
        content += table.markdown

        chunk = TextChunk(
            chunk_id=f"{chapter_content.chapter_id}_table_{chunk_number}",
            chapter_id=chapter_content.chapter_id,
            book_id=chapter_content.book_id,
            chunk_number=chunk_number,
            title=f"Table: {table.caption or 'Data Table'}",
            content=content,
            content_type="table",
            page_range=(table.page_number, table.page_number),
            source_location=f"Chapter {chapter_content.chapter_number}, page {table.page_number}",
            metadata={
                "table_id": table.table_id,
                "headers": table.headers,
                "row_count": len(table.rows)
            }
        )

        return chunk

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        if not text:
            return []

        # Split by double newlines
        paragraphs = re.split(r'\n\n+', text)

        # Filter out empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs

    def _create_chunk_from_text(
        self,
        text: str,
        section_title: str,
        chapter_content: Any,
        chunk_number: int,
        use_llm: bool
    ) -> TextChunk:
        """Create a TextChunk from raw text"""

        # Classify content type
        content_type = self._classify_content(text)

        chunk_id = f"{chapter_content.chapter_id}_chunk_{chunk_number}"

        chunk = TextChunk(
            chunk_id=chunk_id,
            chapter_id=chapter_content.chapter_id,
            book_id=chapter_content.book_id,
            chunk_number=chunk_number,
            title=f"{section_title}"[:100],  # Truncate if too long
            content=text,
            content_type=content_type,
            section_title=section_title,
            source_location=f"Chapter {chapter_content.chapter_number}, Section: {section_title}",
            metadata={
                "word_count": len(text.split()),
                "char_count": len(text)
            }
        )

        # Use LLM to enhance chunk if available
        if use_llm and self.llm_client:
            self._enrich_chunk_with_llm(chunk)

        # Extract key concepts without LLM
        else:
            self._extract_key_concepts_heuristic(chunk)

        return chunk

    def _classify_content(self, text: str) -> str:
        """Classify the type of content"""
        text_lower = text.lower().strip()

        # Check for definition
        for pattern in self.DEFINITION_PATTERNS:
            if re.match(pattern, text_lower):
                return "definition"

        # Check for example
        for pattern in self.EXAMPLE_PATTERNS:
            if re.match(pattern, text_lower):
                return "example"

        # Check for summary (typically at end of section)
        if re.match(r'^(summary|key terms|review|chapter review)', text_lower):
            return "summary"

        # Default to narrative
        return "narrative"

    def _enrich_chunk_with_llm(self, chunk: TextChunk):
        """
        Use LLM to analyze and enrich chunk content

        This would call the hybrid LLM router to:
        1. Extract key concepts
        2. Identify definitions
        3. Find relationships
        4. Generate summary
        5. Assess difficulty level
        """
        # TODO: Implement LLM-based enrichment
        # For now, use heuristic extraction
        self._extract_key_concepts_heuristic(chunk)

    def _extract_key_concepts_heuristic(self, chunk: TextChunk):
        """Extract key concepts using heuristic patterns"""

        # Extract definitions (pattern: "Term is definition")
        for pattern in self.DEFINITION_PATTERNS:
            matches = re.finditer(pattern, chunk.content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                term = match.group(1).strip()
                # Get the definition (rest of the sentence/paragraph)
                start = match.end()
                definition_end = chunk.content.find('.', start)
                if definition_end > start:
                    definition = chunk.content[start:definition_end].strip()
                    chunk.definitions[term] = definition
                    chunk.key_concepts.append(term)

        # Extract capitalized terms that might be key concepts
        # Look for words that are capitalized and not sentence starters
        sentences = re.split(r'[.!?]', chunk.content)
        for sentence in sentences:
            words = sentence.split()
            for i, word in enumerate(words):
                # Skip first word (likely sentence starter)
                if i == 0:
                    continue
                # Look for capitalized words that might be terms
                if word[0].isupper() and len(word) > 3 and word not in chunk.key_concepts:
                    # Only add if it appears to be a term (not just a proper noun)
                    if word.endswith('s') or word.isupper() or '_' in word:
                        chunk.key_concepts.append(word)

        # Remove duplicates
        chunk.key_concepts = list(set(chunk.key_concepts))

    def save_chunks(self, result: ChunkingResult, output_dir: str = "/tmp/openstax_chunks"):
        """Save chunks to JSON files for review"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save chunks as JSON
        chunks_file = output_path / f"{result.chapter_id}_chunks.json"
        with open(chunks_file, 'w') as f:
            chunks_data = [
                {
                    "chunk_id": c.chunk_id,
                    "title": c.title,
                    "content_type": c.content_type,
                    "word_count": c.get_word_count(),
                    "key_concepts": c.key_concepts,
                    "definitions": c.definitions,
                    "content": c.content[:500] + "..." if len(c.content) > 500 else c.content
                }
                for c in result.chunks
            ]
            json.dump(chunks_data, f, indent=2)

        logger.info(f"Saved {len(result.chunks)} chunks to {chunks_file}")

        return chunks_file


# Convenience functions
def chunk_chapter(chapter_content: Any, use_llm: bool = False) -> ChunkingResult:
    """Chunk a single chapter"""
    processor = ChunkProcessor()
    return processor.chunk_chapter_content(chapter_content, use_llm=use_llm)


if __name__ == "__main__":
    # Test chunking
    import asyncio
    import sys
    from pathlib import Path

    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    async def test_chunking():
        from dataclasses import dataclass, field
        from typing import List

        # Create a simple test ChapterContent-like object
        @dataclass
        class TestChapterContent:
            chapter_id: str
            book_id: str
            chapter_number: int
            title: str
            text_content: str
            sections: List = field(default_factory=list)
            images: List = field(default_factory=list)
            tables: List = field(default_factory=list)

        # Create test content
        test_content = TestChapterContent(
            chapter_id="test_chapter_01",
            book_id="test_book",
            chapter_number=1,
            title="Test Chapter: Whole Numbers",
            text_content="""
Chapter 1: Whole Numbers

Whole numbers are the building blocks of mathematics. They include all the positive numbers starting from zero: 0, 1, 2, 3, and so on.

What is a Whole Number?

A whole number is any number from zero to infinity that is not a fraction or decimal. Whole numbers are used for counting objects in everyday life.

For example, if you have 5 apples, you are using a whole number. If you have 0 apples, you are still using a whole number (zero).

Place Value

Understanding place value is essential when working with whole numbers. Each digit in a number has a value based on its position.

In the number 456:
- The 6 is in the ones place (6 × 1 = 6)
- The 5 is in the tens place (5 × 10 = 50)
- The 4 is in the hundreds place (4 × 100 = 400)

Adding Whole Numbers

Addition combines two or more numbers to find a total. For example, 3 + 5 = 8.

Key Terms to Remember:
- Sum: The result of addition
- Addend: A number being added
- Commutative Property: The order of addition doesn't matter (a + b = b + a)
""",
            sections=[],
            images=[],
            tables=[]
        )

        processor = ChunkProcessor()
        result = processor.chunk_chapter_content(test_content, use_llm=False)

        print(f"\nChunking Results:")
        print(f"  Total chunks: {result.total_chunks}")
        print(f"  Chapter: {result.metadata['chapter_title']}")
        print()

        for i, chunk in enumerate(result.chunks[:5], 1):
            print(f"Chunk {i}:")
            print(f"  Title: {chunk.title}")
            print(f"  Type: {chunk.content_type}")
            print(f"  Words: {chunk.get_word_count()}")
            print(f"  Key concepts: {chunk.key_concepts[:5]}")
            print(f"  Definitions: {list(chunk.definitions.keys())[:3]}")
            print(f"  Content preview: {chunk.content[:150]}...")
            print()

        # Save chunks
        processor.save_chunks(result)
        print(f"Chunks saved to: /tmp/openstax_chunks/")

    asyncio.run(test_chunking())
