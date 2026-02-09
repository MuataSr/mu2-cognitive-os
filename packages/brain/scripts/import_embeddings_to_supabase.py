"""
Import OpenStax Embeddings into Supabase
==========================================

Reads the generated embeddings JSON files and imports them into Supabase/pgvector.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import os
import psycopg2
from psycopg2.extras import execute_values

# Add parent directory to path for config import
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import OPENSTAX_EMBEDDINGS_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_embeddings_from_json(json_path: Path) -> List[Dict[str, Any]]:
    """Load embeddings from JSON file"""
    logger.info(f"Loading embeddings from {json_path}...")

    with open(json_path, 'r') as f:
        data = json.load(f)

    chunks = data.get("chunks", [])
    logger.info(f"  Loaded {len(chunks)} chunks")
    return chunks


def create_supabase_client():
    """Create Supabase/PostgreSQL connection"""
    from psycopg2.extras import execute_values

    # Try to get connection string from environment
    url = os.environ.get("DATABASE_URL", "")

    if url and url.startswith("postgresql://"):
        logger.info(f"Using database connection from DATABASE_URL")
        conn = psycopg2.connect(url)
        return conn

    # Otherwise use default local Supabase settings (from docker-compose.yml)
    logger.info(f"Using local Supabase connection")
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "54322")),
        database=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "your-super-secret-and-long-postgres-password")
    )
    return conn


def import_embeddings_to_supabase(chunks: List[Dict[str, Any]], vectors_data: List[Dict[str, Any]]):
    """Import embeddings into Supabase"""

    # Load full vectors
    vectors_map = {v["chunk_id"]: v["embedding"] for v in vectors_data}

    conn = create_supabase_client()
    cursor = conn.cursor()

    try:
        # Enable pgvector extension (may need superuser)
        logger.info("Enabling pgvector extension...")
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception as e:
            conn.rollback()  # Rollback the failed transaction
            if "permission denied" in str(e) or "InsufficientPrivilege" in str(e):
                logger.warning("  Cannot create extension (need superuser), checking if it exists...")
                cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
                if cursor.fetchone():
                    logger.info("  ✓ pgvector extension already exists")
                else:
                    raise Exception("pgvector extension not found. Please run as superuser: CREATE EXTENSION vector;")
            else:
                raise

        # Create table if not exists
        logger.info("Creating textbook_chunks table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS textbook_chunks (
                id BIGSERIAL PRIMARY KEY,
                chunk_id TEXT UNIQUE NOT NULL,
                chapter_id TEXT NOT NULL,
                book_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                embedding vector(768),
                word_count INTEGER NOT NULL,
                key_concepts JSONB DEFAULT '[]'::jsonb,
                definitions JSONB DEFAULT '{}'::jsonb,
                section_title TEXT,
                source_location TEXT,
                embedding_model TEXT NOT NULL DEFAULT 'embeddinggemma:300m',
                embedding_dimension INTEGER NOT NULL DEFAULT 768,
                generated_at TIMESTAMPTZ DEFAULT NOW(),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # Create vector index
        logger.info("Creating vector index...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_textbook_chunks_embedding
            ON textbook_chunks USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)

        # Prepare data for insertion
        logger.info(f"Preparing {len(chunks)} chunks for insertion...")

        insert_data = []
        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            embedding = vectors_map.get(chunk_id)

            if not embedding:
                logger.warning(f"  No embedding found for {chunk_id}, skipping")
                continue

            # Truncate content if too long (Postgres has limits)
            content = chunk.get("content", "")
            if len(content) > 10000:
                content = content[:10000] + "..."

            insert_data.append((
                chunk_id,
                chunk["chapter_id"],
                chunk["book_id"],
                chunk["title"][:500],  # Truncate title
                content,
                chunk["content_type"],
                embedding,  # Full vector
                chunk["word_count"],
                json.dumps(chunk.get("key_concepts", [])),
                json.dumps(chunk.get("definitions", {})),
                chunk.get("section_title"),
                chunk.get("source_location"),
                "embeddinggemma:300m",
                768
            ))

        # Insert in batches
        logger.info(f"Inserting {len(insert_data)} chunks...")

        execute_values(
            cursor,
            """
            INSERT INTO textbook_chunks (
                chunk_id, chapter_id, book_id, title, content, content_type,
                embedding, word_count, key_concepts, definitions,
                section_title, source_location, embedding_model, embedding_dimension
            ) VALUES %s
            ON CONFLICT (chunk_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                word_count = EXCLUDED.word_count,
                key_concepts = EXCLUDED.key_concepts,
                definitions = EXCLUDED.definitions,
                updated_at = NOW()
            """,
            insert_data
        )

        conn.commit()
        logger.info(f"✓ Inserted {len(insert_data)} chunks")

        # Verify
        cursor.execute("SELECT COUNT(*) FROM textbook_chunks")
        count = cursor.fetchone()[0]
        logger.info(f"✓ Total chunks in database: {count}")

    except Exception as e:
        conn.rollback()
        logger.error(f"✗ Import failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def main():
    """Main import function"""

    # Paths
    embeddings_file = OPENSTAX_EMBEDDINGS_DIR / "american-government-3e_embeddings.json"
    vectors_file = OPENSTAX_EMBEDDINGS_DIR / "american-government-3e_vectors.json"

    if not embeddings_file.exists():
        logger.error(f"Embeddings file not found: {embeddings_file}")
        logger.info("Please run the embedding pipeline first")
        return

    if not vectors_file.exists():
        logger.error(f"Vectors file not found: {vectors_file}")
        logger.info("Please run the embedding pipeline first")
        return

    logger.info("=" * 60)
    logger.info("Importing OpenStax Embeddings to Supabase")
    logger.info("=" * 60)

    # Load data
    chunks = load_embeddings_from_json(embeddings_file)

    with open(vectors_file, 'r') as f:
        vectors_data = json.load(f)
        logger.info(f"Loaded {len(vectors_data)} vectors")

    # Import
    import_embeddings_to_supabase(chunks, vectors_data)

    logger.info("\n" + "=" * 60)
    logger.info("Import Complete")
    logger.info("=" * 60)
    logger.info("\nYou can now query the embeddings:")
    logger.info("  SELECT chunk_id, title, 1 - (embedding <=> '[...]') AS similarity")
    logger.info("  FROM textbook_chunks")
    logger.info("  ORDER BY embedding <=> '[...]'")
    logger.info("  LIMIT 5;")


if __name__ == "__main__":
    main()
