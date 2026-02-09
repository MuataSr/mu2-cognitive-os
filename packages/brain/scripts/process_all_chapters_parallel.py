"""
Process All OpenStax Chapters in Parallel
==========================================

Processes all remaining American Government chapters using parallel processing
to reduce total time from ~8 hours to ~5-7 hours.

Features:
- Parallel chapter processing (4 workers)
- Progress tracking
- Automatic retry on failure
- Comprehensive logging
"""

import asyncio
import logging
import sys
import time
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import traceback

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.openstax_content_extractor import OpenStaxContentExtractor
from src.services.openstax_chunk_processor import ChunkProcessor
from src.services.openstax_embedding_service import OllamaEmbeddingService
from src.core.config import OPENSTAX_EMBEDDINGS_DIR, OPENSTAX_CHAPTERS_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SimpleChapterPDF:
    """Simple chapter PDF object for content extraction"""
    pdf_path: Path
    chapter_number: int
    title: str
    page_range: tuple[int, int] = (0, 0)  # Unknown for pre-split chapters
    file_size: int = 0  # Will be set from actual file


class ChapterProcessor:
    """Process a single chapter through the full pipeline"""

    def __init__(self):
        self.content_extractor = OpenStaxContentExtractor()
        self.chunk_processor = ChunkProcessor()
        self.embedding_service = OllamaEmbeddingService(
            base_url="http://localhost:11434",
            model="embeddinggemma:300m",
            batch_size=3,  # Optimal for 100% success
            timeout=180  # Increased from 120 to handle parallel load
        )

    def process_chapter(self, chapter_pdf_path: Path) -> Dict[str, Any]:
        """
        Process a single chapter: extract → chunk → embed

        Args:
            chapter_pdf_path: Path to chapter PDF

        Returns:
            Processing result with metadata
        """
        chapter_name = chapter_pdf_path.stem
        start_time = time.time()

        result = {
            "chapter": chapter_name,
            "success": False,
            "error": None,
            "chunks_created": 0,
            "concepts_extracted": 0,
            "definitions_extracted": 0,
            "time_seconds": 0,
            "embeddings_file": None,
            "vectors_file": None
        }

        try:
            logger.info(f"Processing {chapter_name}...")

            # Extract chapter number and title from filename
            # Format: AmericanGovernment3e_chapterXX_Chapter_Y_Title.pdf
            match = re.search(r'chapter(\d+)', chapter_name)
            if not match:
                raise Exception(f"Could not extract chapter number from {chapter_name}")

            chapter_number = int(match.group(1))

            # Extract title (everything after "Chapter_Y_")
            title_parts = chapter_name.split('_Chapter_')
            if len(title_parts) > 1:
                title = title_parts[1].replace('.pdf', '')
            else:
                title = f"Chapter {chapter_number}"

            # Create chapter PDF object
            chapter_pdf = SimpleChapterPDF(
                pdf_path=chapter_pdf_path,
                chapter_number=chapter_number,
                title=title,
                file_size=chapter_pdf_path.stat().st_size
            )

            # Step 1: Extract content
            logger.info(f"  [{chapter_name}] Extracting content...")
            chapter_data = self.content_extractor.extract_chapter_content(
                chapter_pdf=chapter_pdf,
                book_id="american-government-3e"
            )

            if not chapter_data or not chapter_data.text_content:
                raise Exception(f"No content extracted from {chapter_name}")

            # Step 2: Chunk the content
            logger.info(f"  [{chapter_name}] Chunking...")
            chunking_result = self.chunk_processor.chunk_chapter_content(
                chapter_content=chapter_data
            )
            chunks = chunking_result.chunks

            if not chunks:
                raise Exception(f"No chunks created from {chapter_name}")

            result["chunks_created"] = len(chunks)
            result["concepts_extracted"] = sum(len(c.key_concepts) for c in chunks)
            result["definitions_extracted"] = sum(len(c.definitions) for c in chunks)

            logger.info(f"  [{chapter_name}] Created {len(chunks)} chunks")

            # Step 3: Generate embeddings
            logger.info(f"  [{chapter_name}] Generating embeddings...")
            embedding_result = asyncio.run(self.embedding_service.embed_chunks(
                chunks=chunks,
                show_progress=False
            ))

            # Step 4: Save embeddings (chapter-specific to avoid conflicts)
            logger.info(f"  [{chapter_name}] Saving embeddings...")

            # Check if we got any successful embeddings
            if embedding_result.successful_embeddings == 0:
                raise Exception(f"No embeddings were generated successfully")

            # Prepare chapter-specific data from embedded chunks
            chunks_data = []
            vectors_data = []

            for embedded_chunk in embedding_result.embedded_chunks:
                chunk_dict = {
                    "chunk_id": embedded_chunk.chunk_id,
                    "chapter_id": embedded_chunk.chapter_id,
                    "book_id": embedded_chunk.book_id,
                    "title": embedded_chunk.title,
                    "content_type": embedded_chunk.content_type,
                    "embedding_dimension": len(embedded_chunk.embedding),
                    "embedding_preview": embedded_chunk.embedding[:5],  # First 5 values
                    "word_count": embedded_chunk.word_count,
                    "key_concepts": embedded_chunk.key_concepts,
                    "definitions": embedded_chunk.definitions,
                    "section_title": embedded_chunk.section_title,
                    "source_location": embedded_chunk.source_location
                }
                chunks_data.append(chunk_dict)

                vectors_data.append({
                    "chunk_id": embedded_chunk.chunk_id,
                    "embedding": embedded_chunk.embedding
                })

            # Save chapter embeddings
            chapter_embeddings_file = OPENSTAX_EMBEDDINGS_DIR / f"{chapter_name}_embeddings.json"
            with open(chapter_embeddings_file, 'w') as f:
                json.dump({
                    "metadata": {
                        "chapter": chapter_name,
                        "chapter_number": chapter_number,
                        "title": title,
                        "book_id": "american-government-3e",
                        "total_chunks": len(chunks),
                        "total_concepts": sum(len(c.key_concepts) for c in chunks),
                        "total_definitions": sum(len(c.definitions) for c in chunks),
                        "successful_embeddings": embedding_result.successful_embeddings,
                        "failed_embeddings": embedding_result.failed_embeddings,
                        "generated_at": datetime.now().isoformat()
                    },
                    "chunks": chunks_data
                }, f, indent=2)

            # Save chapter vectors
            chapter_vectors_file = OPENSTAX_EMBEDDINGS_DIR / f"{chapter_name}_vectors.json"
            with open(chapter_vectors_file, 'w') as f:
                json.dump(vectors_data, f, indent=2)

            result["success"] = True
            result["embeddings_file"] = str(chapter_embeddings_file)
            result["vectors_file"] = str(chapter_vectors_file)
            result["time_seconds"] = time.time() - start_time

            logger.info(f"  ✓ [{chapter_name}] Complete in {result['time_seconds']:.1f}s")
            logger.info(f"    Chunks: {result['chunks_created']}, Concepts: {result['concepts_extracted']}, Definitions: {result['definitions_extracted']}")

        except Exception as e:
            result["error"] = str(e)
            result["time_seconds"] = time.time() - start_time
            logger.error(f"  ✗ [{chapter_name}] Failed after {result['time_seconds']:.1f}s: {e}")

        return result


def process_single_chapter(chapter_pdf_path: Path) -> Dict[str, Any]:
    """
    Wrapper function for multiprocessing

    Args:
        chapter_pdf_path: Path to chapter PDF

    Returns:
        Processing result
    """
    processor = ChapterProcessor()
    return processor.process_chapter(chapter_pdf_path)


def get_chapter_pdfs() -> List[Path]:
    """Get all chapter PDFs excluding already processed ones"""
    chapters_dir = Path("/tmp/openstax_chapters")

    # Get all full chapter PDFs (not the small metadata files)
    chapter_pdfs = sorted([
        f for f in chapters_dir.glob("AmericanGovernment3e_chapter*_Chapter_*.pdf")
        if f.stat().st_size > 1000  # Skip small metadata files
    ])

    # Check which chapters are already processed
    processed_chapters = set()
    for embeddings_file in OPENSTAX_EMBEDDINGS_DIR.glob("*_embeddings.json"):
        # Extract chapter number from filename
        if "chapter" in embeddings_file.stem.lower():
            chapter_num = embeddings_file.stem.split("chapter")[1].split("_")[0]
            processed_chapters.add(f"chapter{chapter_num}")

    # Filter out already processed chapters
    remaining_chapters = []
    for pdf_path in chapter_pdfs:
        chapter_num = pdf_path.stem.split("chapter")[1].split("_")[0]
        if f"chapter{chapter_num}" not in processed_chapters:
            remaining_chapters.append(pdf_path)

    return remaining_chapters


def save_progress(results: List[Dict[str, Any]], output_file: Path):
    """Save processing progress to JSON file"""
    progress_data = {
        "timestamp": datetime.now().isoformat(),
        "total_chapters": len(results),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "total_time_seconds": sum(r["time_seconds"] for r in results),
        "total_chunks": sum(r.get("chunks_created", 0) for r in results),
        "total_concepts": sum(r.get("concepts_extracted", 0) for r in results),
        "total_definitions": sum(r.get("definitions_extracted", 0) for r in results),
        "results": results
    }

    with open(output_file, 'w') as f:
        json.dump(progress_data, f, indent=2)


def print_progress_summary(results: List[Dict[str, Any]], start_time: float):
    """Print a summary of processing progress"""
    completed = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    total = len(results)
    elapsed = time.time() - start_time

    logger.info("=" * 70)
    logger.info("PROCESSING SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Completed: {completed}/{total} chapters")
    logger.info(f"Failed: {failed}/{total} chapters")
    logger.info(f"Total time: {timedelta(seconds=int(elapsed))}")
    logger.info(f"Average time per chapter: {elapsed / total:.1f}s")
    logger.info(f"Total chunks: {sum(r.get('chunks_created', 0) for r in results)}")
    logger.info(f"Total concepts: {sum(r.get('concepts_extracted', 0) for r in results)}")
    logger.info(f"Total definitions: {sum(r.get('definitions_extracted', 0) for r in results)}")

    if failed > 0:
        logger.info("\nFailed chapters:")
        for r in results:
            if not r["success"]:
                logger.info(f"  - {r['chapter']}: {r.get('error', 'Unknown error')}")

    logger.info("=" * 70)


def main():
    """Process all remaining chapters in parallel"""

    logger.info("=" * 70)
    logger.info("Processing All OpenStax Chapters in Parallel")
    logger.info("=" * 70)

    start_time = time.time()

    # Get remaining chapters
    chapters = get_chapter_pdfs()

    if not chapters:
        logger.info("No remaining chapters to process!")
        return

    logger.info(f"\nFound {len(chapters)} chapters to process")
    logger.info(f"Estimated time: {len(chapters) * 15 / 60:.1f} minutes (parallel)")
    logger.info("")

    # Process chapters in parallel
    # Use 2 workers to avoid overwhelming Ollama API (reduced from 4 due to timeouts)
    max_workers = 2
    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all chapters
        future_to_chapter = {
            executor.submit(process_single_chapter, chapter): chapter
            for chapter in chapters
        }

        logger.info(f"Processing with {max_workers} parallel workers...")
        logger.info("")

        # Collect results as they complete
        for future in as_completed(future_to_chapter):
            chapter = future_to_chapter[future]
            try:
                result = future.result()
                results.append(result)

                # Print progress
                completed = len([r for r in results if r["success"]])
                total = len(chapters)
                pct = (completed / total) * 100
                logger.info(f"Progress: {completed}/{total} ({pct:.1f}%) - Current: {result['chapter']} - {'✓' if result['success'] else '✗'}")

                # Save progress incrementally
                progress_file = OPENSTAX_EMBEDDINGS_DIR / "processing_progress.json"
                save_progress(results, progress_file)

            except Exception as e:
                logger.error(f"Chapter {chapter} raised exception: {e}")
                traceback.print_exc()
                results.append({
                    "chapter": chapter.stem,
                    "success": False,
                    "error": str(e),
                    "time_seconds": 0
                })

    # Print final summary
    print_progress_summary(results, start_time)

    # Save final results
    results_file = OPENSTAX_EMBEDDINGS_DIR / f"processing_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    save_progress(results, results_file)
    logger.info(f"\n✓ Results saved to: {results_file}")

    logger.info("\nNext steps:")
    logger.info("1. Import all embeddings to PostgreSQL:")
    logger.info("   python3 scripts/import_embeddings_to_supabase.py")
    logger.info("2. Rebuild knowledge graph with all concepts:")
    logger.info("   python3 src/services/openstax_knowledge_graph.py")


if __name__ == "__main__":
    main()
