"""
Test Semantic Search with OpenStax Embeddings
================================================

Demonstrates vector similarity search using the stored OpenStax embeddings.
"""

import logging
import json
import psycopg2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add parent directory to path for config import
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import OPENSTAX_EMBEDDINGS_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SemanticSearchEngine:
    """Semantic search using pgvector"""

    def __init__(self):
        self.conn = psycopg2.connect(
            host='localhost',
            port=54322,
            database='postgres',
            user='postgres',
            password='your-super-secret-and-long-postgres-password'
        )
        self.cursor = self.conn.cursor()

    def search_similar(
        self,
        query_text: str = None,
        query_embedding: List[float] = None,
        limit: int = 10,
        book_id: str = None,
        content_type: str = None,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity

        Args:
            query_text: Text to search for (requires embedding generation)
            query_embedding: Pre-computed embedding vector
            limit: Maximum number of results
            book_id: Filter by book ID
            content_type: Filter by content type
            threshold: Minimum similarity score (0-1)

        Returns:
            List of similar chunks with metadata
        """
        if query_embedding:
            embedding = query_embedding
        else:
            raise ValueError("Either query_text or query_embedding must be provided")

        # Convert to PostgreSQL vector format
        vector_str = '[' + ','.join(map(str, embedding)) + ']'

        # Build query
        query = f"""
            SELECT
                chunk_id,
                chapter_id,
                book_id,
                title,
                content_type,
                word_count,
                key_concepts,
                definitions,
                section_title,
                1 - (embedding <=> '{vector_str}'::vector) AS similarity
            FROM textbook_chunks
            WHERE 1 - (embedding <=> '{vector_str}'::vector) > {threshold}
        """

        params = []

        if book_id:
            query += " AND book_id = %s"
            params.append(book_id)

        if content_type:
            query += " AND content_type = %s"
            params.append(content_type)

        query += f" ORDER BY embedding <=> '{vector_str}'::vector LIMIT {limit};"

        self.cursor.execute(query, params)
        results = self.cursor.fetchall()

        # Format results
        formatted_results = []
        for row in results:
            # Handle JSONB fields - they come as different types from psycopg2
            key_concepts = row[6] if row[6] else []
            if isinstance(key_concepts, str):
                key_concepts = json.loads(key_concepts)

            definitions = row[7] if row[7] else {}
            if isinstance(definitions, str):
                definitions = json.loads(definitions)

            formatted_results.append({
                'chunk_id': row[0],
                'chapter_id': row[1],
                'book_id': row[2],
                'title': row[3],
                'content_type': row[4],
                'word_count': row[5],
                'key_concepts': key_concepts,
                'definitions': definitions,
                'section_title': row[8],
                'similarity': float(row[9])
            })

        return formatted_results

    def get_chunk_content(self, chunk_id: str) -> Dict[str, Any]:
        """Get full content of a chunk"""
        self.cursor.execute(
            "SELECT * FROM textbook_chunks WHERE chunk_id = %s",
            (chunk_id,)
        )
        row = self.cursor.fetchone()

        if not row:
            return None

        # Handle JSONB fields (key_concepts at index 9, definitions at index 10)
        key_concepts = row[9] if row[9] else []
        if isinstance(key_concepts, str):
            key_concepts = json.loads(key_concepts)

        definitions = row[10] if row[10] else {}
        if isinstance(definitions, str):
            definitions = json.loads(definitions)

        return {
            'chunk_id': row[1],
            'chapter_id': row[2],
            'book_id': row[3],
            'title': row[4],
            'content': row[5],
            'content_type': row[6],
            'word_count': row[8],
            'key_concepts': key_concepts,
            'definitions': definitions,
            'section_title': row[11],
            'source_location': row[12],
            'similarity': 1.0  # Self-similarity
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        self.cursor.execute("SELECT COUNT(*) FROM textbook_chunks")
        total_chunks = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(*) FROM textbook_chunks WHERE content_type = 'narrative'")
        narrative_count = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(*) FROM textbook_chunks WHERE content_type = 'table'")
        table_count = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT DISTINCT book_id FROM textbook_chunks")
        books = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("SELECT AVG(word_count) FROM textbook_chunks")
        avg_word_count = self.cursor.fetchone()[0] or 0

        return {
            'total_chunks': total_chunks,
            'narrative_chunks': narrative_count,
            'table_chunks': table_count,
            'books': books,
            'avg_word_count': round(avg_word_count, 1)
        }

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


def load_test_embeddings() -> Dict[str, List[float]]:
    """Load embeddings for testing"""
    vectors_file = OPENSTAX_EMBEDDINGS_DIR / "american-government-3e_vectors.json"

    if not vectors_file.exists():
        raise FileNotFoundError(f"Vectors file not found: {vectors_file}")

    with open(vectors_file, 'r') as f:
        vectors_data = json.load(f)

    return {v["chunk_id"]: v["embedding"] for v in vectors_data}


def test_semantic_search():
    """Test semantic search functionality"""

    logger.info("=" * 60)
    logger.info("Testing Semantic Search with OpenStax Embeddings")
    logger.info("=" * 60)

    # Initialize search engine
    search = SemanticSearchEngine()

    # Load test embeddings
    logger.info("\nLoading embeddings...")
    embeddings = load_test_embeddings()
    logger.info(f"✓ Loaded {len(embeddings)} embeddings")

    # Get database stats
    logger.info("\nDatabase Statistics:")
    stats = search.get_stats()
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # Test 1: Exact match (should return similarity = 1.0)
    logger.info("\n" + "-" * 60)
    logger.info("Test 1: Exact Match Search")
    logger.info("-" * 60)

    test_chunk_id = "american-government-3e_chapter01_chunk_1"
    test_embedding = embeddings[test_chunk_id]

    results = search.search_similar(
        query_embedding=test_embedding,
        limit=5
    )

    logger.info(f"Query chunk: {test_chunk_id}")
    logger.info("")
    logger.info("Results:")
    for i, result in enumerate(results[:5], 1):
        logger.info(f"  {i}. {result['chunk_id']}")
        logger.info(f"     Similarity: {result['similarity']:.4f}")
        logger.info(f"     Type: {result['content_type']}")
        logger.info(f"     Concepts: {', '.join(result['key_concepts'][:5])}")
        logger.info("")

    # Test 2: Filter by content type (narrative only)
    logger.info("-" * 60)
    logger.info("Test 2: Narrative Content Only")
    logger.info("-" * 60)

    results = search.search_similar(
        query_embedding=test_embedding,
        limit=5,
        content_type="narrative"
    )

    logger.info(f"Query chunk: {test_chunk_id} (narrative only)")
    logger.info("")
    logger.info("Results:")
    for i, result in enumerate(results[:5], 1):
        logger.info(f"  {i}. {result['chunk_id']}")
        logger.info(f"     Similarity: {result['similarity']:.4f}")
        logger.info("")

    # Test 3: Different chunk
    logger.info("-" * 60)
    logger.info("Test 3: Search with Different Chunk")
    logger.info("-" * 60)

    test_chunk_id_2 = "american-government-3e_chapter01_table_22"
    test_embedding_2 = embeddings[test_chunk_id_2]

    results = search.search_similar(
        query_embedding=test_embedding_2,
        limit=5
    )

    logger.info(f"Query chunk: {test_chunk_id_2} (table)")
    logger.info("")
    logger.info("Results:")
    for i, result in enumerate(results[:5], 1):
        logger.info(f"  {i}. {result['chunk_id']}")
        logger.info(f"     Similarity: {result['similarity']:.4f}")
        logger.info(f"     Type: {result['content_type']}")
        logger.info("")

    # Test 4: High threshold (only very similar)
    logger.info("-" * 60)
    logger.info("Test 4: High Similarity Threshold (>0.9)")
    logger.info("-" * 60)

    results = search.search_similar(
        query_embedding=test_embedding,
        limit=10,
        threshold=0.9
    )

    logger.info(f"Query chunk: {test_chunk_id} (threshold > 0.9)")
    logger.info(f"Found {len(results)} results")
    logger.info("")
    for i, result in enumerate(results[:5], 1):
        logger.info(f"  {i}. {result['chunk_id']}")
        logger.info(f"     Similarity: {result['similarity']:.4f}")
        logger.info("")

    # Test 5: Get full chunk content
    logger.info("-" * 60)
    logger.info("Test 5: Retrieve Full Chunk Content")
    logger.info("-" * 60)

    chunk = search.get_chunk_content(test_chunk_id)
    if chunk:
        logger.info(f"Chunk: {chunk['chunk_id']}")
        logger.info(f"Title: {chunk['title'][:80]}...")
        logger.info(f"Type: {chunk['content_type']}")
        logger.info(f"Word count: {chunk['word_count']}")
        logger.info(f"Concepts: {', '.join(chunk['key_concepts'][:10])}")
        logger.info(f"Definitions: {list(chunk['definitions'].keys())[:5]}")
        logger.info(f"Content preview: {chunk['content'][:200]}...")
    else:
        logger.error(f"Could not retrieve chunk: {test_chunk_id}")

    # Close connection
    search.close()

    logger.info("\n" + "=" * 60)
    logger.info("Semantic Search Tests Complete")
    logger.info("=" * 60)


def main():
    """Run semantic search tests"""
    test_semantic_search()


if __name__ == "__main__":
    main()
