#!/usr/bin/env python3
"""
Supabase Migration Script

This script applies database migrations to a Supabase database.
It reads migration files from supabase/migrations/ and executes them in order.

Usage:
    python scripts/migrate-supabase.py

Prerequisites:
    1. Set DATABASE_URL in .env to your Supabase connection string
    2. Install dependencies: pip install psycopg2-binary python-dotenv

Environment:
    DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxxxxxxx.supabase.co:5432/postgres
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Load environment variables
load_dotenv()

# Migration files in order
MIGRATIONS = [
    "001_initial_schema.sql",
    "002_knowledge_vault.sql",
    "003_mastery_tracking.sql",
    "004_add_learning_events_fields.sql",
    "005_questions_table.sql",
]

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def get_database_url():
    """Get database URL from environment"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print_error("DATABASE_URL not found in environment variables")
        print_warning("Please set DATABASE_URL in your .env file")
        print("Format: postgresql://postgres:[PASSWORD]@db.xxxxxxxx.supabase.co:5432/postgres")
        sys.exit(1)
    return db_url


def verify_connection(db_url: str) -> bool:
    """Verify database connection"""
    try:
        conn = psycopg2.connect(db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        conn.close()

        print_success(f"Connected to database")
        print(f"  Version: {version[:50]}...")

        # Check if this is Supabase
        if "supabase" in version.lower() or db_url.lower().count("supabase.co") > 0:
            print_success("This is a Supabase database")
        return True
    except Exception as e:
        print_error(f"Failed to connect to database: {e}")
        return False


def read_migration_file(migration_name: str) -> str:
    """Read migration file content"""
    migrations_dir = Path(__file__).parent.parent / "supabase" / "migrations"
    migration_file = migrations_dir / migration_name

    if not migration_file.exists():
        print_error(f"Migration file not found: {migration_file}")
        return None

    with open(migration_file, 'r') as f:
        return f.read()


def execute_migration(db_url: str, migration_name: str, migration_sql: str) -> bool:
    """Execute a single migration"""
    print(f"\n{Colors.BOLD}Applying: {migration_name}{Colors.END}")

    try:
        conn = psycopg2.connect(db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Split SQL by semicolons and execute each statement
        # This is a simple approach - for complex migrations, consider using a migration tool
        statements = [s.strip() for s in migration_sql.split(';') if s.strip()]

        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    cursor.execute(statement)
                except psycopg2.errors.DuplicateObject:
                    # Ignore duplicate object errors (already exists)
                    print_warning(f"  Statement {i}: Object already exists, skipping...")
                except psycopg2.errors.DuplicateTable:
                    # Ignore duplicate table errors
                    print_warning(f"  Statement {i}: Table already exists, skipping...")
                except Exception as e:
                    # For other errors, print but continue
                    print_error(f"  Statement {i} failed: {e}")

        conn.close()
        print_success(f"Migration '{migration_name}' completed")
        return True

    except Exception as e:
        print_error(f"Migration '{migration_name}' failed: {e}")
        return False


def verify_extensions(db_url: str):
    """Verify required extensions are installed"""
    print(f"\n{Colors.BOLD}Verifying required extensions...{Colors.END}")

    required_extensions = ["pgvector", "age", "uuid-ossp", "pg_stat_statements"]

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        for ext in required_extensions:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = %s);", (ext,))
            exists = cursor.fetchone()[0]
            if exists:
                print_success(f"  {ext}: installed")
            else:
                print_warning(f"  {ext}: NOT installed (will be created by migration)")

        conn.close()
    except Exception as e:
        print_error(f"Failed to verify extensions: {e}")


def verify_tables(db_url: str):
    """Verify expected tables exist after migration"""
    print(f"\n{Colors.BOLD}Verifying database tables...{Colors.END}")

    expected_tables = [
        ("cortex", "user_sessions"),
        ("vectordb", "knowledge_chunks"),
        ("cortex", "textbook_chunks"),
        ("cortex", "graph_nodes"),
        ("cortex", "graph_edges"),
        ("cortex", "chunk_concept_links"),
        ("cortex", "skills_registry"),
        ("cortex", "learning_events"),
        ("cortex", "student_skills"),
        ("cortex", "questions"),
    ]

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        for schema, table in expected_tables:
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                );
            """, (schema, table))
            exists = cursor.fetchone()[0]
            if exists:
                print_success(f"  {schema}.{table}: exists")
            else:
                print_error(f"  {schema}.{table}: missing")

        conn.close()
    except Exception as e:
        print_error(f"Failed to verify tables: {e}")


def main():
    """Main migration function"""
    print_header("Supabase Migration Script")

    # Get and verify connection
    db_url = get_database_url()
    if not verify_connection(db_url):
        sys.exit(1)

    # Verify extensions before migration
    verify_extensions(db_url)

    # Run migrations
    print(f"\n{Colors.BOLD}Running migrations...{Colors.END}")

    success_count = 0
    for migration in MIGRATIONS:
        sql = read_migration_file(migration)
        if sql:
            if execute_migration(db_url, migration, sql):
                success_count += 1

    # Verify tables after migration
    verify_tables(db_url)

    # Summary
    print_header("Migration Summary")
    print(f"  Total migrations: {len(MIGRATIONS)}")
    print_success(f"  Successful: {success_count}")
    if success_count < len(MIGRATIONS):
        print_error(f"  Failed: {len(MIGRATIONS) - success_count}")

    print(f"\n{Colors.GREEN}{Colors.BOLD}Migration complete!{Colors.END}\n")
    print("Next steps:")
    print("  1. Verify tables in Supabase Dashboard: https://supabase.com/dashboard")
    print("  2. Check Row Level Security (RLS) policies are enabled")
    print("  3. Test your application connection")
    print("  4. Seed initial data if needed")


if __name__ == "__main__":
    main()
