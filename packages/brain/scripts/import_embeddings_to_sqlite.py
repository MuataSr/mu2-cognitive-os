"""
Import OpenStax Embeddings into SQLite (Fallback)
================================================

Stores embeddings in SQLite with vector similarity search capability.
Use this when pgvector is not available in PostgreSQL.
"""

import asyncio
import json
import logging
import sqlite3
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add parent directory to path for config import
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import OPENSTAX_CHUNKS_DIR, OPENSTAX_EMBEDDINGS_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    a_arr = np.array(a)
    b_arr = np.array(b)
    return np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr))


class SQLiteEmbeddingStore:
    """SQLite-based embedding store with vector similarity search"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(OPENSTAX_CHUNKS_DIR / "chunks.db")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Create chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT UNIQUE NOT NULL,
                chapter_id TEXT NOT NULL,
                book_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                word_count INTEGER NOT NULL,
                key_concepts TEXT,  -- JSON array
                definitions TEXT,   -- JSON object
                section_title TEXT,
                source_location TEXT,
                embedding_model TEXT NOT NULL DEFAULT 'embeddinggemma:300m',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create embeddings table (separate for efficiency)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,  -- numpy array as bytes
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
            );
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_book_id ON chunks(book_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_chapter_id ON chunks(chapter_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_content_type ON chunks(content_type);")

        self.conn.commit()
        logger.info(f"✓ Database initialized: {self.db_path}")

    def insert_chunk(self, chunk: Dict[str, Any], embedding: List[float]):
        """Insert a chunk with its embedding"""
        cursor = self.conn.cursor()

        # Insert chunk metadata
        cursor.execute("""
            INSERT OR REPLACE INTO chunks (
                chunk_id, chapter_id, book_id, title, content, content_type,
                word_count, key_concepts, definitions, section_title, source_location, embedding_model
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk["chunk_id"],
            chunk["chapter_id"],
            chunk["book_id"],
            chunk["title"][:500],
            chunk.get("content", "")[:10000],  # Truncate long content
            chunk["content_type"],
            chunk["word_count"],
            json.dumps(chunk.get("key_concepts", [])),
            json.dumps(chunk.get("definitions", {})),
            chunk.get("section_title"),
            chunk.get("source_location"),
            "embeddinggemma:300m"
        ))

        # Insert embedding as bytes
        embedding_array = np.array(embedding, dtype=np.float32)
        cursor.execute("""
            INSERT OR REPLACE INTO embeddings (chunk_id, embedding)
            VALUES (?, ?)
        """, (chunk["chunk_id"], embedding_array.tobytes()))

        self.conn.commit()

    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        book_id: str = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks by embedding"""
        cursor = self.conn.cursor()

        # Build query
        if book_id:
            cursor.execute("""
                SELECT c.*, e.embedding
                FROM chunks c
                JOIN embeddings e ON c.chunk_id = e.chunk_id
                WHERE c.book_id = ?
                ORDER BY c.id
            """, (book_id,))
        else:
            cursor.execute("""
                SELECT c.*, e.embedding
                FROM chunks c
                JOIN embeddings e ON c.chunk_id = e.chunk_id
                ORDER BY c.id
            """)

        results = []
        for row in cursor.fetchall():
            # Calculate similarity
            stored_embedding = np.frombuffer(row["embedding"], dtype=np.float32)
            similarity = cosine_similarity(query_embedding, stored_embedding)

            results.append({
                "chunk_id": row["chunk_id"],
                "chapter_id": row["chapter_id"],
                "book_id": row["book_id"],
                "title": row["title"],
                "content": row["content"],
                "content_type": row["content_type"],
                "similarity": float(similarity),
                "key_concepts": json.loads(row["key_concepts"] if row["key_concepts"] else "[]"),
                "definitions": json.loads(row["definitions"] if row["definitions"] else "{}")
            })

        # Sort by similarity and return top results
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM chunks")
        total_chunks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM embeddings")
        total_embeddings = cursor.fetchone()[0]

        cursor.execute("SELECT DISTINCT book_id FROM chunks")
        books = [row[0] for row in cursor.fetchall()]

        return {
            "total_chunks": total_chunks,
            "total_embeddings": total_embeddings,
            "books": books
        }


def import_embeddings_to_sqlite(
    chunks: List[Dict[str, Any]],
    vectors_data: List[Dict[str, Any]],
    db_path: str = None
):
    """Import embeddings into SQLite"""

    if db_path is None:
        db_path = str(OPENSTAX_CHUNKS_DIR / "chunks.db")

    store = SQLiteEmbeddingStore(db_path)
    vectors_map = {v["chunk_id"]: v["embedding"] for v in vectors_data}

    logger.info(f"Importing {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        chunk_id = chunk["chunk_id"]
        embedding = vectors_map.get(chunk_id)

        if not embedding:
            logger.warning(f"  No embedding for {chunk_id}, skipping")
            continue

        store.insert_chunk(chunk, embedding)

        if (i + 1) % 10 == 0:
            logger.info(f"  Imported {i + 1}/{len(chunks)} chunks")

    stats = store.get_stats()
    logger.info(f"\n✓ Import complete!")
    logger.info(f"  Total chunks: {stats['total_chunks']}")
    logger.info(f"  Total embeddings: {stats['total_embeddings']}")
    logger.info(f"  Books: {stats['books']}")

    return store


def main():
    """Main import function"""

    # Paths
    embeddings_file = OPENSTAX_EMBEDDINGS_DIR / "american-government-3e_embeddings.json"
    vectors_file = OPENSTAX_EMBEDDINGS_DIR / "american-government-3e_vectors.json"

    if not embeddings_file.exists():
        logger.error(f"Embeddings file not found: {embeddings_file}")
        return

    if not vectors_file.exists():
        logger.error(f"Vectors file not found: {vectors_file}")
        return

    logger.info("=" * 60)
    logger.info("Importing OpenStax Embeddings to SQLite")
    logger.info("=" * 60)

    # Load data
    with open(embeddings_file, 'r') as f:
        data = json.load(f)
        chunks = data.get("chunks", [])
        logger.info(f"Loaded {len(chunks)} chunks metadata")

    with open(vectors_file, 'r') as f:
        vectors_data = json.load(f)
        logger.info(f"Loaded {len(vectors_data)} vectors")

    # Import
    store = import_embeddings_to_sqlite(chunks, vectors_data)

    # Test similarity search
    logger.info("\n" + "=" * 60)
    logger.info("Testing Similarity Search")
    logger.info("=" * 60)

    if chunks:
        # Use first chunk's embedding as query
        test_chunk_id = chunks[0]["chunk_id"]
        vectors_map = {v["chunk_id"]: v["embedding"] for v in vectors_data}
        query_embedding = vectors_map[test_chunk_id]

        results = store.search_similar(query_embedding, limit=5)

        logger.info(f"\nTop 5 similar chunks to '{test_chunk_id}':")
        for i, result in enumerate(results, 1):
            logger.info(f"  {i}. {result['chunk_id']}")
            logger.info(f"     Similarity: {result['similarity']:.4f}")
            logger.info(f"     Title: {result['title'][:60]}...")
            logger.info(f"     Concepts: {', '.join(result['key_concepts'][:3])}")
            logger.info("")

    logger.info("=" * 60)
    logger.info(f"Database Location: {OPENSTAX_CHUNKS_DIR / 'chunks.db'}")
    logger.info("=" * 60)
    logger.info("\nTo enable PostgreSQL/pgvector support:")
    logger.info("  1. Access the database with superuser privileges:")
    logger.info("     docker exec mu2-db psql -U postgres -d postgres")
    logger.info("  2. Create the pgvector extension:")
    logger.info("     CREATE EXTENSION IF NOT EXISTS vector;")
    logger.info("  3. Run the migration:")
    logger.info("     psql -h localhost -p 54322 -U postgres -d postgres -f supabase/migrations/005_openstax_embeddings.sql")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
