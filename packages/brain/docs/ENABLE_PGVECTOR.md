# Enable pgvector in Supabase

## Current Situation

The local Docker database does not have the pgvector extension installed, and we don't have superuser access to create it. Here are several ways to enable it:

## Option 1: Enable via Supabase Dashboard (Recommended for Remote)

If you're using the remote Supabase instance:

1. Go to https://supabase.com/dashboard
2. Select your project (opnytxqhikmqgmcgnkto)
3. Go to **Database** → **Extensions**
4. Find and enable **vector** (pgvector)
5. Click **Confirm**

## Option 2: Enable via Local Docker (Requires Superuser)

When you have superuser access to the Docker container:

```bash
# Method A: Using docker exec (requires sudo or passwordless docker)
sudo docker exec mu2-db psql -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Method B: Using psql directly
PGPASSWORD=your-super-secret-and-long-postgres-password \
  psql -h localhost -p 54322 -U postgres -d postgres \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Method C: Using Python script
python3 scripts/enable_pgvector.sh
```

## Option 3: Recreate Database Container with pgvector

Stop the existing container and recreate it with pgvector:

```bash
# Stop and remove container (requires sudo)
sudo docker-compose down

# Update docker-compose.yml to use pgvector-enabled image
# The supabase/postgres:15.14.1.081 image should have pgvector

# Start fresh
sudo docker-compose up -d
```

## Option 4: Use SQLite Instead (Current Working Solution)

The embeddings are already stored in SQLite with similarity search:

```bash
# Query the SQLite database
sqlite3 data/openstax/chunks/chunks.db
SELECT * FROM chunks LIMIT 5;

# Use Python API
python3 -c "
from scripts.import_embeddings_to_sqlite import SQLiteEmbeddingStore
store = SQLiteEmbeddingStore('data/openstax/chunks/chunks.db')
stats = store.get_stats()
print(stats)
"
```

## Running the Migration After pgvector is Enabled

Once pgvector is enabled, run the migration:

```bash
# Via psql
PGPASSWORD=your-super-secret-and-long-postgres-password \
  psql -h localhost -p 54322 -U postgres -d postgres \
  -f supabase/migrations/005_openstax_embeddings.sql

# Or via Python script
python3 scripts/import_embeddings_to_supabase.py
```

## Verification

Check if pgvector is enabled:

```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=54322,
    database='postgres',
    user='postgres',
    password='your-super-secret-and-long-postgres-password'
)
cursor = conn.cursor()
cursor.execute(\"SELECT extname FROM pg_extension WHERE extname = 'vector';\")
result = cursor.fetchone()
if result:
    print('✓ pgvector is installed')
else:
    print('✗ pgvector is NOT installed')
cursor.close()
conn.close()
"
```

## Quick Test

After enabling pgvector, test vector operations:

```sql
-- Test vector type
SELECT '[1,2,3]'::vector;

-- Test cosine similarity
SELECT 1 - ('[1,2,3]'::vector <=> '[1,2,3]'::vector) AS similarity;
-- Should return: 1.0

-- Check ivfflat index support
SELECT amname FROM pg_am WHERE amname = 'ivfflat';
```

## Current Status

- ✅ Embeddings generated (29 chunks, 768-dim vectors)
- ✅ SQLite import working with similarity search
- ❌ PostgreSQL/pgvector not available (requires superuser)

## Next Steps

1. Enable pgvector using one of the methods above
2. Run the migration script to create the table
3. Import embeddings into PostgreSQL
4. Test vector similarity search
