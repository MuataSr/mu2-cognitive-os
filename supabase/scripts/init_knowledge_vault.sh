#!/bin/bash
# ============================================================================
# Knowledge Vault Initialization Script
# Mu2 Cognitive OS - Sprint 2, Task 2.1
# ============================================================================

set -e  # Exit on error

echo "============================================================================"
echo "KNOWLEDGE VAULT INITIALIZATION"
echo "Mu2 Cognitive OS - Hybrid RAG System"
echo "============================================================================"
echo ""

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-54322}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-postgres}"
PGPASSWORD="${POSTGRES_PASSWORD:-your-super-secret-and-long-postgres-password}"

export PGPASSWORD

echo "Database Configuration:"
echo "  Host: ${DB_HOST}"
echo "  Port: ${DB_PORT}"
echo "  User: ${DB_USER}"
echo "  Database: ${DB_NAME}"
echo ""

# Function to check if database is ready
check_db_ready() {
    echo "Checking if database is ready..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
            echo "✓ Database is ready!"
            return 0
        fi
        echo "  Waiting for database... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    echo "✗ Database connection failed after $max_attempts attempts"
    return 1
}

# Function to run SQL file
run_sql_file() {
    local file="$1"
    local description="$2"

    echo ""
    echo "Running: $description"
    echo "File: $file"

    if [ ! -f "$file" ]; then
        echo "✗ File not found: $file"
        return 1
    fi

    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$file"; then
        echo "✓ $description completed successfully"
        return 0
    else
        echo "✗ $description failed"
        return 1
    fi
}

# Function to initialize Apache AGE graph
init_age_graph() {
    echo ""
    echo "Initializing Apache AGE graph: kda_curriculum"

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- Load AGE extension
LOAD 'age';
SET search_path TO ag_catalog, "$user", public;

-- Create graph
DO $$
BEGIN
    PERFORM create_graph('kda_curriculum');
    RAISE NOTICE '✓ Graph kda_curriculum created successfully';
EXCEPTION
    WHEN duplicate_table THEN
        RAISE NOTICE 'ℹ Graph kda_curriculum already exists';
END $$;

-- Verify graph creation
SELECT graphname FROM ag_graph WHERE graphname = 'kda_curriculum';
EOF

    if [ $? -eq 0 ]; then
        echo "✓ Apache AGE graph initialization complete"
        return 0
    else
        echo "✗ Apache AGE graph initialization failed"
        return 1
    fi
}

# Main execution
main() {
    echo "============================================================================"
    echo "STEP 1: Database Connectivity Check"
    echo "============================================================================"

    if ! check_db_ready; then
        echo ""
        echo "ERROR: Cannot connect to database. Please ensure:"
        echo "  1. Docker is running: docker-compose up -d"
        echo "  2. Database port is accessible: ${DB_PORT}"
        echo "  3. Password is correctly set in environment"
        exit 1
    fi

    echo ""
    echo "============================================================================"
    echo "STEP 2: Running Migrations"
    echo "============================================================================"

    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    MIGRATIONS_DIR="$(dirname "$SCRIPT_DIR")/migrations"

    # Run migration 001 if it exists
    if [ -f "$MIGRATIONS_DIR/001_initial_schema.sql" ]; then
        run_sql_file "$MIGRATIONS_DIR/001_initial_schema.sql" "Migration 001: Initial Schema"
    fi

    # Run migration 002
    if [ -f "$MIGRATIONS_DIR/002_knowledge_vault.sql" ]; then
        run_sql_file "$MIGRATIONS_DIR/002_knowledge_vault.sql" "Migration 002: Knowledge Vault"
    else
        echo "✗ Migration file 002_knowledge_vault.sql not found"
        exit 1
    fi

    echo ""
    echo "============================================================================"
    echo "STEP 3: Initializing Apache AGE Graph"
    echo "============================================================================"

    init_age_graph

    echo ""
    echo "============================================================================"
    echo "STEP 4: Seeding Graph Data"
    echo "============================================================================"

    if [ -f "$MIGRATIONS_DIR/seed_graph.sql" ]; then
        run_sql_file "$MIGRATIONS_DIR/seed_graph.sql" "Graph Seed Data"
    else
        echo "✗ Seed file seed_graph.sql not found"
        exit 1
    fi

    echo ""
    echo "============================================================================"
    echo "STEP 5: Running Tests"
    echo "============================================================================"

    TESTS_DIR="$(dirname "$SCRIPT_DIR")/tests"
    if [ -f "$TESTS_DIR/test_knowledge_vault.sql" ]; then
        run_sql_file "$TESTS_DIR/test_knowledge_vault.sql" "Knowledge Vault Tests"
    else
        echo "ℹ Test file not found, skipping tests"
    fi

    echo ""
    echo "============================================================================"
    echo "INITIALIZATION COMPLETE"
    echo "============================================================================"
    echo ""
    echo "Knowledge Vault is ready for use!"
    echo ""
    echo "Next Steps:"
    echo "  1. Start the Brain API: cd apps/brain && uvicorn src.main:app --reload"
    echo "  2. Access Supabase Studio: http://localhost:3000"
    echo "  3. Query the database:"
    echo "     psql -h localhost -p 54322 -U postgres -d postgres"
    echo ""
    echo "Available Functions:"
    echo "  - cortex.search_similar_chunks(embedding, grade_level, subject, limit, threshold)"
    echo "  - cortex.get_concept_context(concept_label)"
    echo ""
    echo "Available Views:"
    echo "  - cortex.chunk_with_concepts"
    echo "  - cortex.graph_statistics"
    echo "  - cortex.curriculum_graph_stats"
    echo ""
}

# Run main function
main "$@"
