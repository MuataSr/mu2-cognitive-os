# Knowledge Vault Deployment Checklist

**Sprint 2, Task 2.1 | Ready for Deployment**

## Pre-Deployment Checklist

### Prerequisites

- [ ] Docker is installed and running
- [ ] User has Docker permissions (or can use sudo)
- [ ] Port 54322 is available for database
- [ ] Environment variables are set in `.env` file

### Environment Variables

Create `.env` file in project root:

```bash
# Database
DB_HOST=localhost
DB_PORT=54322
DB_USER=postgres
DB_NAME=postgres
POSTGRES_PASSWORD=your-super-secret-and-long-postgres-password

# Auth
JWT_SECRET=your-super-secret-jwt-token-with-at-least-32-characters-long
JWT_EXPIRY=3600

# API
API_EXTERNAL_URL=http://localhost:9999
SITE_URL=http://localhost:3000
```

## Deployment Steps

### Step 1: Start Docker Containers

```bash
cd /home/papi/Documents/mu2-cognitive-os
docker-compose up -d
```

**Verify:**
```bash
docker-compose ps
```

Expected output: All services showing "Up" or "healthy"

### Step 2: Initialize Knowledge Vault

```bash
./supabase/scripts/init_knowledge_vault.sh
```

This will:
1. Check database connectivity
2. Run migration 001 (initial schema)
3. Run migration 002 (knowledge vault)
4. Initialize Apache AGE graph `kda_curriculum`
5. Seed graph data with science concepts
6. Run test suite
7. Report status

### Step 3: Verify Deployment

#### Option A: Run SQL Tests

```bash
# Set password
export PGPASSWORD="your-super-secret-and-long-postgres-password"

# Run tests
psql -h localhost -p 54322 -U postgres -d postgres \
  -f supabase/tests/test_knowledge_vault.sql
```

Expected output: All tests pass with ✓ marks

#### Option B: Run Python Tests

```bash
cd packages/brain
python tests/test_knowledge_vault.py
```

Expected output: All tests pass with green ✓ marks

#### Option C: Manual Verification

```bash
# Connect to database
export PGPASSWORD="your-super-secret-and-long-postgres-password"
psql -h localhost -p 54322 -U postgres -d postgres
```

Then run:
```sql
-- Check tables exist
\dt cortex.*

-- Check graph exists
SELECT graphname FROM ag_graph;

-- Count nodes
SELECT COUNT(*) FROM cortex.graph_nodes WHERE graph_name = 'kda_curriculum';

-- Count edges
SELECT COUNT(*) FROM cortex.graph_edges WHERE graph_name = 'kda_curriculum';

-- Test vector search
SELECT * FROM cortex.search_similar_chunks(
    '[0.1, 0.2, 0.3, 0.4, 0.5]'::vector(1536),
    8, 'science', 5, 0.5
);

-- Test graph context
SELECT * FROM cortex.get_concept_context('Photosynthesis');
```

Expected results:
- 8 tables in cortex schema
- Graph `kda_curriculum` exists
- ~50 nodes, ~40 edges
- Functions return results

## Post-Deployment Verification

### Database Structure

```sql
-- Verify all tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'cortex'
ORDER BY table_name;
```

Expected tables:
- `active_sessions` (view)
- `chunk_concept_links`
- `graph_edges`
- `graph_nodes`
- `textbook_chunks`
- `user_sessions`

### Verify Indexes

```sql
-- Check vector index
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'cortex' AND indexname = 'idx_textbook_embeddings';
```

Expected: HNSW index using vector_cosine_ops

### Verify RLS Policies

```sql
-- Check RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'cortex';
```

Expected: All tables show rowsecurity = true

```sql
-- Check policies exist
SELECT schemaname, tablename, policyname
FROM pg_policies
WHERE schemaname = 'cortex';
```

Expected: Multiple policies for each table

### Verify Graph Data

```sql
-- Domain statistics
SELECT * FROM cortex.curriculum_graph_stats;
```

Expected: 4 domains (Biology, Physics, Chemistry, Earth Science)

### Verify Functions

```sql
-- Check functions exist
SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_schema = 'cortex'
ORDER BY routine_name;
```

Expected functions:
- `get_concept_context`
- `search_similar_chunks`
- `update_updated_at`

## Integration Tests

### Test 1: Vector Search

```sql
-- Insert test chunk
INSERT INTO cortex.textbook_chunks (
    chapter_id, section_id, content, embedding, grade_level, subject
) VALUES (
    'test', 'test',
    'Test content about photosynthesis',
    '[0.1, 0.2, 0.3, 0.4, 0.5]'::vector(1536),
    8, 'science'
);

-- Search for similar chunks
SELECT * FROM cortex.search_similar_chunks(
    '[0.1, 0.2, 0.3, 0.4, 0.5]'::vector(1536),
    8, 'science', 5, 0.5
);

-- Clean up
DELETE FROM cortex.textbook_chunks WHERE chapter_id = 'test';
```

### Test 2: Graph Traversal

```sql
-- Get photosynthesis context
SELECT * FROM cortex.get_concept_context('Photosynthesis');

-- Expected: Concepts like Sunlight, Oxygen, Glucose, etc.
```

### Test 3: Hybrid Query

```sql
-- Chunks with concepts
SELECT
    chapter_id,
    section_id,
    LEFT(content, 50) as preview,
    related_concepts
FROM cortex.chunk_with_concepts
WHERE related_concepts IS NOT NULL
LIMIT 5;
```

## Troubleshooting

### Issue: "Database connection refused"

**Solution:**
```bash
# Check if containers are running
docker-compose ps

# If not running, start them
docker-compose up -d

# Check logs
docker-compose logs db -f
```

### Issue: "Extension pgvector not found"

**Solution:**
```bash
# Restart db container to load extensions
docker-compose restart db

# Wait for healthy status
docker-compose ps
```

### Issue: "Graph kda_curriculum not found"

**Solution:**
```sql
-- Manually create graph
LOAD 'age';
SET search_path TO ag_catalog, "$user", public;
SELECT create_graph('kda_curriculum');
```

### Issue: "RLS policy blocking queries"

**Solution:**
```sql
-- Check current user
SELECT current_user;

-- Check JWT token
SELECT auth.jwt();

-- Verify role in JWT
SELECT auth.jwt() ->> 'role';
```

### Issue: "Port 54322 already in use"

**Solution:**
```bash
# Check what's using the port
lsof -i :54322

# Change port in .env
DB_PORT=54323

# Restart with new port
docker-compose down
docker-compose up -d
```

## Performance Validation

### Vector Search Performance

```sql
EXPLAIN ANALYZE
SELECT * FROM cortex.search_similar_chunks(
    '[0.1, 0.2, 0.3, 0.4, 0.5]'::vector(1536),
    8, 'science', 10, 0.7
);
```

Expected: Uses index scan, < 10ms for 1000 chunks

### Graph Query Performance

```sql
EXPLAIN ANALYZE
SELECT * FROM cortex.get_concept_context('Photosynthesis');
```

Expected: < 5ms for typical queries

## Monitoring

### Check Database Size

```sql
-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'cortex'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Check Index Usage

```sql
-- Index statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'cortex'
ORDER BY idx_scan DESC;
```

### Check Connection Count

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'postgres';
```

## Rollback Procedure

If needed, rollback database changes:

```bash
# Stop containers
docker-compose down -v

# Remove volumes (⚠️ deletes all data)
docker volume rm mu2-cognitive-os_docker-volumes-db

# Restart fresh
docker-compose up -d

# Re-run initialization
./supabase/scripts/init_knowledge_vault.sh
```

## Success Criteria

Deployment is successful when:

- [ ] All Docker containers are running and healthy
- [ ] Migration 002 applied successfully
- [ ] `kda_curriculum` graph exists with ~50 nodes
- [ ] All tests pass (SQL and Python)
- [ ] Vector search returns results
- [ ] Graph traversal returns relationships
- [ ] RLS policies are active
- [ ] Documentation is accessible

## Production Readiness

Before moving to production:

- [ ] Real textbook content loaded (not just samples)
- [ ] Embeddings generated via Ollama (not dummy values)
- [ ] Authentication fully configured
- [ ] Backup strategy implemented
- [ ] Monitoring configured
- [ ] Performance baselines established
- [ ] Security audit completed
- [ ] FERPA compliance verified

## Support Documentation

- **Full Guide:** `/docs/KNOWLEDGE_VAULT.md`
- **Quick Reference:** `/docs/KNOWLEDGE_VAULT_QUICKREF.md`
- **Architecture:** `/docs/ARCHITECTURE_DIAGRAMS.md`
- **Implementation Report:** `/docs/SPRINT_2_TASK_2_1_REPORT.md`

## Contact

For issues or questions:
- Check troubleshooting section above
- Review documentation in `/docs/`
- Check logs: `docker-compose logs db -f`

---

**Status:** Ready for deployment
**Last Updated:** 2026-02-07
**Version:** 1.0.0
