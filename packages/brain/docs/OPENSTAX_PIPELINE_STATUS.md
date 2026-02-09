# OpenStax Textbook Ingestion Pipeline

## Overview

The OpenStax textbook ingestion pipeline converts OpenStax PDF textbooks into vector embeddings for semantic search and knowledge graph integration.

## Pipeline Components

### 1. TOC Extractor (`openstax_toc_extractor.py`)
- Extracts table of contents from PDF outlines
- Identifies chapter boundaries (start/end pages)
- Handles OpenStax-specific PDF outline format (dict-based with `/Title`, `/Page` keys)
- Resolves page numbers from IndirectObjects

**Input:** OpenStax PDF textbook
**Output:** List of `Chapter` objects with page ranges

### 2. PDF Splitter (`openstax_pdf_splitter.py`)
- Splits large textbooks into individual chapter PDFs
- Creates self-contained chapter PDFs (pages 0-N)
- Saves to `/tmp/openstax_chapters/`

**Input:** Textbook PDF + Chapter TOC data
**Output:** Individual chapter PDF files

### 3. Content Extractor (`openstax_content_extractor.py`)
- Extracts structured content from chapter PDFs
- Uses pdfplumber for text extraction
- Extracts sections, tables, images, metadata
- Handles large text content (75K+ characters)

**Input:** Chapter PDF file
**Output:** `ChapterContent` object with:
- `text_content`: Full chapter text
- `sections`: List of sections with titles and content
- `tables`: Extracted tables with markdown
- `images`: Image metadata
- `metadata`: Chapter info (number, title, etc.)

### 4. Chunk Processor (`openstax_chunk_processor.py`)
- Intelligently chunks content into learnable segments (500-800 words)
- Respects section boundaries
- Preserves context with 50-word overlap
- Classifies content types (narrative, definition, example, table, summary)
- Extracts key concepts and definitions using heuristics

**Input:** `ChapterContent` object
**Output:** `ChunkingResult` with list of `TextChunk` objects:
- `chunk_id`: Unique identifier
- `content`: Chunk text
- `content_type`: Classification
- `key_concepts`: Extracted concepts
- `definitions`: Extracted term->definition mappings
- `word_count`: Text length
- `metadata`: Additional info

**Chunking Parameters:**
- `TARGET_CHUNK_SIZE`: 500 words
- `MAX_CHUNK_SIZE`: 800 words
- `MIN_CHUNK_SIZE`: 200 words
- `CHUNK_OVERLAP`: 50 words

### 5. Embedding Service (`openstax_embedding_service.py`)
- Generates embeddings using Ollama's local models
- Model: `embeddinggemma:300m` (768 dimensions)
- Batch processing (default: 3 chunks in parallel for optimal performance)
- Saves embeddings in JSON format for Supabase/pgvector import

**Input:** List of `TextChunk` objects
**Output:** `EmbeddingResult` with `EmbeddedChunk` objects:
- 768-dimensional vectors
- Metadata (model, dimension, timestamp)
- Chunk data with concepts and definitions

**Ollama API Details:**
- Endpoint: `http://localhost:11434/api/embeddings`
- Model: `embeddinggemma:300m`
- Timeout: 120 seconds per request
- Average processing time: ~32 seconds per chunk

**Batch Size Optimization:**
| Batch Size | Success Rate | Avg Time/Chunk | Recommendation |
|------------|--------------|----------------|----------------|
| 1 | 100% | 32.79s | Reliable but slower |
| 2 | 100% | 32.67s | Good option |
| **3** | **100%** | **32.47s** | **Optimal** ✓ |
| 5 | 60% | 24.03s | ReadTimeout errors - NOT recommended |

## Current Status

### American Government 3e - Chapter 1 Results

**Extraction:**
- Title: "Chapter 1 American Government and Civic Engagement"
- Text length: 75,244 characters
- Sections: 12
- Tables: 8

**Chunking:**
- Total chunks: 29
- Average chunk size: 434 words
- Content types: 21 narrative, 8 tables
- Total key concepts extracted: 159
- Total definitions extracted: 10

**Embeddings:**
- Model: embeddinggemma:300m (768 dimensions)
- **With batch_size=5:** 22/29 (76%) - ReadTimeout errors on concurrent requests
- **With batch_size=3:** 29/29 (100%) - All chunks processed successfully ✅
- Average time: ~32 seconds per chunk (with batch_size=3)

**Output Files:**
- `/tmp/openstax_embeddings/american-government-3e_embeddings.json` - Embeddings metadata
- `/tmp/openstax_embeddings/american-government-3e_vectors.json` - Full vectors for import

### Prealgebra 2e - Chapter 1 Results

**Issue:** Text extraction is incomplete
- Only 573 characters extracted (circled letters)
- 53 tables found
- Likely cause: PDF encoding/custom fonts in math PDF

**Workaround:** American Government content works fine and is most critical for Civics EOC

## Test Scripts

### `test_local_pdfs.py`
Tests the full pipeline on locally downloaded OpenStax PDFs:
1. Scans `~/Downloads/openstax_pdfs/` for PDFs
2. Extracts TOC and splits into chapters
3. Extracts content from each chapter
4. Displays results with statistics

### `test_chunk_pipeline.py`
Tests chunking only:
1. Extracts content from a chapter PDF
2. Chunks into learnable segments
3. Displays chunk analysis

### `test_embedding_pipeline.py`
Tests the full pipeline with embeddings:
1. Extracts content from chapter PDF
2. Chunks into learnable segments
3. Generates embeddings
4. Saves results

## Data Models

### Chapter (TOC)
```python
@dataclass
class Chapter:
    chapter_number: int
    title: str
    start_page: int
    end_page: Optional[int]
    level: int  # 0 for chapter, 1 for section, etc.
```

### ChapterPDF
```python
@dataclass
class ChapterPDF:
    chapter_number: int
    title: str
    pdf_path: Path
    page_range: Tuple[int, int]  # (start, end) in original PDF
    file_size: int
```

### ChapterContent
```python
@dataclass
class ChapterContent:
    chapter_id: str
    book_id: str
    chapter_number: int
    title: str
    text_content: str
    sections: List[Section]
    images: List[Image]
    tables: List[Table]
    metadata: Dict[str, Any]
```

### TextChunk
```python
@dataclass
class TextChunk:
    chunk_id: str
    chapter_id: str
    book_id: str
    chunk_number: int
    title: str
    content: str
    content_type: str  # "narrative", "definition", "example", "table", "summary"
    key_concepts: List[str]
    definitions: Dict[str, str]
    # ... metadata fields
```

### EmbeddedChunk
```python
@dataclass
class EmbeddedChunk:
    chunk_id: str
    chapter_id: str
    book_id: str
    content: str
    title: str
    content_type: str
    embedding: List[float]  # 768-dimensional vector
    word_count: int
    key_concepts: List[str]
    definitions: Dict[str, str]
    # ... metadata
```

## Next Steps

### 1. ~~Investigate Embedding Failures~~ ✅ COMPLETED
- **Root cause identified:** batch_size=5 caused ReadTimeout errors due to concurrent request limits
- **Solution implemented:** Reduced default batch_size from 5 to 3
- **Result:** 100% success rate achieved with batch_size=3
- **Error handling:** Improved error logging to show chunk ID and specific error message

### 2. Store Embeddings in Vector Store
- Create Supabase/pgvector migration
- Import embeddings using `american-government-3e_vectors.json`
- Add indexing for similarity search

### 3. Knowledge Graph Integration
- Link extracted concepts to graph nodes
- Create relationships between related concepts
- Build topic hierarchy from section structure

### 4. Fix Prealgebra Text Extraction (Optional)
- Try PyPDF2 as alternative to pdfplumber
- Add OCR fallback for math symbols
- Focus on American Government first (higher priority)

### 5. Process Additional Books
- American Government has 35 chapters total
- Process all chapters for complete coverage
- Add other OpenStax books as needed

## Commands

```bash
# Run full pipeline test
cd packages/brain
python3 test_embedding_pipeline.py

# Test chunking only
python3 test_chunk_pipeline.py

# Test embedding service
python3 -m src.services.openstax_embedding_service

# Process local PDFs
python3 test_local_pdfs.py
```

## Configuration

**Ollama Model:**
```bash
# Pull the embedding model
ollama pull embeddinggemma:300m

# Verify model is available
ollama list
```

**File Locations:**
- Input PDFs: `~/Downloads/openstax_pdfs/`
- Chapter PDFs: `/tmp/openstax_chapters/`
- Embeddings: `/tmp/openstax_embeddings/`
- Chunks: `/tmp/openstax_chunks/`

## Performance Metrics

**American Government Chapter 1:**
- Extraction time: ~9 seconds
- Chunking time: <1 second
- Embedding time: ~563 seconds (9.4 minutes)
- Total pipeline time: ~572 seconds (9.5 minutes)

**Per-chunk embedding time (with batch_size=3):**
- Average: 32.47 seconds per chunk
- 100% success rate (all chunks processed)

**Success Rate (with batch_size=3):**
- Chunks created: 29/29 (100%)
- Embeddings generated: 29/29 (100%) ✅
- Concepts extracted: 159
- Definitions extracted: 10

## Troubleshooting

### Issue: ~~Embeddings fail silently~~ ✅ FIXED
**Solution:** Updated error logging to show chunk ID and error message; reduced batch_size to 3

### Issue: ~~ReadTimeout errors with batch_size=5~~ ✅ FIXED
**Solution:** Reduced default batch_size from 5 to 3 for 100% success rate

### Issue: Prealgebra text extraction fails
**Solution:** Try PyPDF2 or OCR; American Government works fine

### Issue: Ollama model not found
**Solution:** Run `ollama pull embeddinggemma:300m`

### Issue: Empty embedding response
**Solution:** Check Ollama is running with `ollama serve`

## References

- OpenStax: https://openstax.org/
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
- embeddinggemma:300m: 768-dimensional embedding model
- Supabase pgvector: https://supabase.com/docs/guides/ai/vector-columns
