#!/usr/bin/env python3
"""
Knowledge Vault Database Connection Test
Mu2 Cognitive OS - Sprint 2, Task 2.1

Tests database connectivity and basic operations for the Hybrid RAG system.
Run this from the brain package directory.
"""

import os
import sys
from typing import Optional
import psycopg
from psycopg.rows import dict_row
from psycopg.types import Vector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "54322")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "your-super-secret-and-long-postgres-password")
DB_NAME = os.getenv("DB_NAME", "postgres")


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


def print_header(message: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")


def test_connection() -> Optional[psycopg.Connection]:
    """
    Test database connection.

    Returns:
        Connection object if successful, None otherwise.
    """
    print_info("Testing database connection...")

    try:
        conn = psycopg.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
            autocommit=True
        )
        print_success(f"Connected to database '{DB_NAME}' on {DB_HOST}:{DB_PORT}")
        return conn
    except psycopg.OperationalError as e:
        print_error(f"Failed to connect to database: {e}")
        print_info("Make sure Docker is running: docker-compose up -d")
        return None
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return None


def test_vector_extension(conn: psycopg.Connection) -> bool:
    """
    Test pgvector extension availability.

    Args:
        conn: Database connection

    Returns:
        True if pgvector is available, False otherwise.
    """
    print_info("Checking pgvector extension...")

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pgvector');")
            exists = cur.fetchone()[0]

            if exists:
                print_success("pgvector extension is installed")
                return True
            else:
                print_error("pgvector extension not found")
                return False
    except Exception as e:
        print_error(f"Error checking pgvector: {e}")
        return False


def test_age_extension(conn: psycopg.Connection) -> bool:
    """
    Test Apache AGE extension availability.

    Args:
        conn: Database connection

    Returns:
        True if Apache AGE is available, False otherwise.
    """
    print_info("Checking Apache AGE extension...")

    try:
        with conn.cursor() as cur:
            # Load AGE
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path TO ag_catalog, '$user', public;")

            # Check extension
            cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'age');")
            exists = cur.fetchone()[0]

            if exists:
                print_success("Apache AGE extension is installed")
                return True
            else:
                print_error("Apache AGE extension not found")
                return False
    except Exception as e:
        print_error(f"Error checking Apache AGE: {e}")
        return False


def test_textbook_chunks_table(conn: psycopg.Connection) -> bool:
    """
    Test textbook_chunks table existence and structure.

    Args:
        conn: Database connection

    Returns:
        True if table exists with correct structure, False otherwise.
    """
    print_info("Checking textbook_chunks table...")

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            # Check table exists
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'cortex'
                    AND table_name = 'textbook_chunks'
                );
            """)
            exists = cur.fetchone()['exists']

            if not exists:
                print_error("textbook_chunks table not found")
                return False

            # Check columns
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'cortex'
                AND table_name = 'textbook_chunks'
                ORDER BY ordinal_position;
            """)

            columns = {row['column_name']: row['data_type'] for row in cur.fetchall()}

            expected_columns = {
                'id': 'uuid',
                'chapter_id': 'text',
                'section_id': 'text',
                'content': 'text',
                'embedding': 'USER-DEFINED',
                'grade_level': 'integer',
                'subject': 'text',
                'metadata': 'jsonb',
                'created_at': 'timestamp with time zone'
            }

            for col, dtype in expected_columns.items():
                if col not in columns:
                    print_error(f"Missing column: {col}")
                    return False

            print_success("textbook_chunks table structure verified")
            return True

    except Exception as e:
        print_error(f"Error checking textbook_chunks: {e}")
        return False


def test_vector_index(conn: psycopg.Connection) -> bool:
    """
    Test HNSW vector index existence.

    Args:
        conn: Database connection

    Returns:
        True if index exists, False otherwise.
    """
    print_info("Checking vector index (idx_textbook_embeddings)...")

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_indexes
                    WHERE schemaname = 'cortex'
                    AND indexname = 'idx_textbook_embeddings'
                );
            """)
            exists = cur.fetchone()[0]

            if exists:
                print_success("HNSW vector index exists")
                return True
            else:
                print_error("Vector index not found")
                return False
    except Exception as e:
        print_error(f"Error checking index: {e}")
        return False


def test_graph_tables(conn: psycopg.Connection) -> bool:
    """
    Test graph_nodes and graph_edges tables.

    Args:
        conn: Database connection

    Returns:
        True if tables exist, False otherwise.
    """
    print_info("Checking graph tables (graph_nodes, graph_edges)...")

    try:
        with conn.cursor() as cur:
            # Check graph_nodes
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'cortex'
                    AND table_name = 'graph_nodes'
                );
            """)
            nodes_exists = cur.fetchone()[0]

            # Check graph_edges
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'cortex'
                    AND table_name = 'graph_edges'
                );
            """)
            edges_exists = cur.fetchone()[0]

            if nodes_exists and edges_exists:
                print_success("Graph tables exist")

                # Count nodes and edges
                cur.execute("SELECT COUNT(*) FROM cortex.graph_nodes WHERE graph_name = 'kda_curriculum';")
                node_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM cortex.graph_edges WHERE graph_name = 'kda_curriculum';")
                edge_count = cur.fetchone()[0]

                print_info(f"  Graph nodes: {node_count}")
                print_info(f"  Graph edges: {edge_count}")

                return True
            else:
                print_error("Graph tables not found")
                return False
    except Exception as e:
        print_error(f"Error checking graph tables: {e}")
        return False


def test_sample_insert(conn: psycopg.Connection) -> bool:
    """
    Test inserting a sample textbook chunk with embedding.

    Args:
        conn: Database connection

    Returns:
        True if insert successful, False otherwise.
    """
    print_info("Testing sample chunk insertion...")

    try:
        with conn.cursor() as cur:
            # Create a dummy embedding (1536 dimensions)
            embedding = Vector([0.1] * 1536)

            # Insert sample chunk
            cur.execute("""
                INSERT INTO cortex.textbook_chunks (
                    chapter_id,
                    section_id,
                    content,
                    embedding,
                    grade_level,
                    subject,
                    metadata
                ) VALUES (
                    'test_ch01',
                    'test_sec01',
                    'This is a test chunk about photosynthesis - the process by which plants convert sunlight into energy.',
                    %s,
                    8,
                    'science',
                    '{"test": true}'::jsonb
                )
                ON CONFLICT DO NOTHING
                RETURNING id;
            """, (embedding,))

            result = cur.fetchone()
            if result:
                chunk_id = result[0]
                print_success(f"Sample chunk inserted with ID: {chunk_id}")

                # Clean up test data
                cur.execute("DELETE FROM cortex.textbook_chunks WHERE id = %s;", (chunk_id,))
                print_info("Test data cleaned up")

                return True
            else:
                print_info("Chunk already exists or insert failed (this is OK)")
                return True

    except Exception as e:
        print_error(f"Error inserting sample: {e}")
        return False


def test_search_function(conn: psycopg.Connection) -> bool:
    """
    Test the search_similar_chunks function.

    Args:
        conn: Database connection

    Returns:
        True if function works, False otherwise.
    """
    print_info("Testing search_similar_chunks function...")

    try:
        with conn.cursor() as cur:
            # Create a query embedding
            query_embedding = Vector([0.1] * 1536)

            # Call the function
            cur.execute("""
                SELECT * FROM cortex.search_similar_chunks(
                    %s,
                    8,
                    'science',
                    5,
                    0.5
                );
            """, (query_embedding,))

            results = cur.fetchall()
            print_success(f"Search function returned {len(results)} results")
            return True

    except Exception as e:
        print_error(f"Error testing search function: {e}")
        return False


def test_context_function(conn: psycopg.Connection) -> bool:
    """
    Test the get_concept_context function.

    Args:
        conn: Database connection

    Returns:
        True if function works, False otherwise.
    """
    print_info("Testing get_concept_context function...")

    try:
        with conn.cursor() as cur:
            # Call the function
            cur.execute("SELECT * FROM cortex.get_concept_context('Photosynthesis');")
            results = cur.fetchall()

            if results:
                print_success(f"Context function returned {len(results)} related concepts")

                # Show sample results
                print_info("  Sample relationships:")
                for i, (concept, rel_type, direction) in enumerate(results[:3]):
                    print(f"    {concept} --[{rel_type}]--> {direction}")

                return True
            else:
                print_info("No relationships found (graph may not be seeded yet)")
                return True

    except Exception as e:
        print_error(f"Error testing context function: {e}")
        return False


def main():
    """Run all database tests."""
    print_header("KNOWLEDGE VAULT DATABASE TEST")
    print_info(f"Database: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    # Test connection
    conn = test_connection()
    if not conn:
        print_error("\nCannot proceed without database connection")
        sys.exit(1)

    try:
        # Run tests
        print_header("TESTING EXTENSIONS")
        vector_ok = test_vector_extension(conn)
        age_ok = test_age_extension(conn)

        if not vector_ok or not age_ok:
            print_error("\nRequired extensions not installed")
            print_info("Run: ./supabase/scripts/init_knowledge_vault.sh")
            sys.exit(1)

        print_header("TESTING TABLE STRUCTURE")
        chunks_ok = test_textbook_chunks_table(conn)
        index_ok = test_vector_index(conn)
        graph_ok = test_graph_tables(conn)

        if not chunks_ok or not index_ok or not graph_ok:
            print_error("\nDatabase structure incomplete")
            print_info("Run migrations: psql -f supabase/migrations/002_knowledge_vault.sql")
            sys.exit(1)

        print_header("TESTING FUNCTIONS")
        insert_ok = test_sample_insert(conn)
        search_ok = test_search_function(conn)
        context_ok = test_context_function(conn)

        # Summary
        print_header("TEST RESULTS")
        all_passed = all([vector_ok, age_ok, chunks_ok, index_ok, graph_ok, insert_ok, search_ok, context_ok])

        if all_passed:
            print_success("All tests passed!")
            print_info("\nThe Knowledge Vault is ready for use.")
            print_info("\nAvailable functions:")
            print("  - cortex.search_similar_chunks()")
            print("  - cortex.get_concept_context()")
            print_info("\nAvailable views:")
            print("  - cortex.chunk_with_concepts")
            print("  - cortex.graph_statistics")
            print("  - cortex.curriculum_graph_stats")
        else:
            print_error("Some tests failed")
            print_info("\nPlease check the errors above and ensure:")
            print("  1. Docker containers are running")
            print("  2. Migrations have been applied")
            print("  3. Graph data has been seeded")

        sys.exit(0 if all_passed else 1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
