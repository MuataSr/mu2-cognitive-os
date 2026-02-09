#!/bin/bash
# Enable pgvector Extension in Supabase
# ===================================
# Run this script when you have superuser access to the database
#
# Usage:
#   ./enable_pgvector.sh          # Local database
#   ./enable_pgvector.sh remote   # Remote Supabase

set -e

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-54322}"
DB_NAME="${DB_NAME:-postgres}"
DB_USER="${DB_USER:-postgres}"

echo "=================================================="
echo "Enabling pgvector Extension"
echo "=================================================="
echo "Host: $DB_HOST:$DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo ""

if [ "$1" = "remote" ]; then
    echo "Using remote Supabase instance..."
    # Extract credentials from .env
    SUPABASE_URL=$(grep "DATABASE_URL=" /home/papi/Documents/mu2-cognitive-os/.env | cut -d'=' -f2)
    echo "Connecting to: $SUPABASE_URL"
    echo ""
    echo "Note: Remote Supabase instances typically have pgvector pre-installed."
    echo "If you get a permission error, enable it in the Supabase dashboard:"
    echo "  1. Go to https://supabase.com/dashboard"
    echo "  2. Select your project"
    echo "  3. Database > Extensions"
    echo "  4. Enable 'vector' extension"
    echo ""
    exit 0
fi

# Check for Docker
if command -v docker &> /dev/null; then
    echo "Found Docker, attempting to create extension..."
    echo ""

    # Try docker exec (requires no sudo)
    if docker exec mu2-db psql -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null; then
        echo "✓ pgvector extension enabled via Docker"
        exit 0
    else
        echo "Docker exec requires sudo or passwordless docker access"
        echo "Please run manually:"
        echo "  sudo docker exec mu2-db psql -U postgres -d postgres -c \"CREATE EXTENSION IF NOT EXISTS vector;\""
    fi
fi

# Try using Python psycopg2
echo ""
echo "Attempting with Python..."
python3 -c "
import psycopg2
import sys

try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port=$DB_PORT,
        database='$DB_NAME',
        user='$DB_USER',
        password='your-super-secret-and-long-postgres-password'
    )
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    print('✓ pgvector extension enabled via Python')
    cursor.close()
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'Failed: {e}')
    print('')
    print('Please run manually with psql:')
    print(f\"  PGPASSWORD=your-super-secret-and-long-postgres-password psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c 'CREATE EXTENSION IF NOT EXISTS vector;'\")
    sys.exit(1)
"

echo ""
echo "=================================================="
echo "Verifying pgvector extension..."
echo "=================================================="

python3 -c "
import psycopg2

conn = psycopg2.connect(
    host='$DB_HOST',
    port=$DB_PORT,
    database='$DB_NAME',
    user='$DB_USER',
    password='your-super-secret-and-long-postgres-password'
)
cursor = conn.cursor()

# Check if extension exists
cursor.execute(\"SELECT extname FROM pg_extension WHERE extname = 'vector';\")
result = cursor.fetchone()

if result:
    print('✓ pgvector extension is installed')
    print('')

    # Show vector type
    cursor.execute(\"SELECT typname FROM pg_type WHERE typname = 'vector';\")
    if cursor.fetchone():
        print('✓ vector type is available')
    else:
        print('✗ vector type not found')
else:
    print('✗ pgvector extension is NOT installed')
    print('   Please run the commands above with superuser privileges')

cursor.close()
conn.close()
"
