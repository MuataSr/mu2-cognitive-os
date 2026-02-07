# Knowledge Vault - Quick Reference

**Fast reference for database operations and queries.**

## Database Connection

```bash
# Command line
psql -h localhost -p 54322 -U postgres -d postgres

# With password
export PGPASSWORD="your-super-secret-and-long-postgres-password"
psql -h localhost -p 54322 -U postgres -d postgres
```

## Common Queries

### Check Table Exists
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'cortex';
```

### Count Chunks
```sql
SELECT COUNT(*) FROM cortex.textbook_chunks;
```

### View Graph Statistics
```sql
SELECT * FROM cortex.graph_statistics;
SELECT * FROM cortex.curriculum_graph_stats;
```

### List All Concepts by Domain
```sql
SELECT
    properties->>'domain' as domain,
    label,
    properties->>'description' as description
FROM cortex.graph_nodes
WHERE graph_name = 'kda_curriculum'
ORDER BY domain, label;
```

### Find Photosynthesis Relationships
```sql
SELECT
    start.label as from_concept,
    e.edge_label as relationship,
    end.label as to_concept,
    e.properties
FROM cortex.graph_edges e
JOIN cortex.graph_nodes start ON e.start_node_id = start.node_id
JOIN cortex.graph_nodes end ON e.end_node_id = end.node_id
WHERE start.label = 'Photosynthesis' OR end.label = 'Photosynthesis';
```

### Search Similar Chunks
```sql
-- Replace embedding array with actual query embedding
SELECT * FROM cortex.search_similar_chunks(
    '[0.1, 0.2, 0.3, 0.4, 0.5]'::vector(1536),
    8,      -- grade_level
    'science', -- subject
    10,     -- limit
    0.7     -- threshold
);
```

### Get Concept Context
```sql
SELECT * FROM cortex.get_concept_context('Photosynthesis');
```

### View Chunks with Linked Concepts
```sql
SELECT
    chapter_id,
    section_id,
    LEFT(content, 80) as preview,
    jsonb_array_length(related_concepts) as concept_count
FROM cortex.chunk_with_concepts
WHERE related_concepts IS NOT NULL
LIMIT 10;
```

## Apache AGE Cypher Queries

```sql
-- Load AGE
LOAD 'age';
SET search_path TO ag_catalog, "$user", public;

-- Find all concepts related to Photosynthesis
SELECT * FROM cypher('kda_curriculum', $$
    MATCH (a:Concept {label: 'Photosynthesis'})-[r]-(b:Concept)
    RETURN a.label as from_concept, type(r) as relationship, b.label as to_concept
$$) as (from_concept text, relationship text, to_concept text);

-- Find shortest path between two concepts
SELECT * FROM cypher('kda_curriculum', $$
    MATCH path = shortestPath(
        (a:Concept {label: 'Cell'})-[*]-(b:Concept {label: 'Energy'})
    )
    RETURN path
$$) as (path agtype);

-- Find all concepts in Biology domain
SELECT * FROM cypher('kda_curriculum', $$
    MATCH (n:Concept)
    WHERE n.properties.domain = 'Biology'
    RETURN n.label as concept, n.properties.description as description
$$) as (concept text, description text);
```

## Testing

```bash
# Run SQL tests
psql -h localhost -p 54322 -U postgres -d postgres \
  -f supabase/tests/test_knowledge_vault.sql

# Run Python tests
cd packages/brain
python tests/test_knowledge_vault.py
```

## Troubleshooting

### Database not running
```bash
docker-compose up -d
docker-compose ps
```

### Check logs
```bash
docker-compose logs db -f
```

### Recreate from scratch
```bash
docker-compose down -v
docker-compose up -d
./supabase/scripts/init_knowledge_vault.sh
```

### Check extensions
```sql
SELECT extname FROM pg_extension WHERE extname IN ('pgvector', 'age');
```

### Check graph
```sql
SELECT graphname FROM ag_graph;
```

## File Locations

| File | Path |
|------|------|
| Migration 002 | `/supabase/migrations/002_knowledge_vault.sql` |
| Graph Seed | `/supabase/migrations/seed_graph.sql` |
| Tests | `/supabase/tests/test_knowledge_vault.sql` |
| Init Script | `/supabase/scripts/init_knowledge_vault.sh` |
| Python Test | `/packages/brain/tests/test_knowledge_vault.py` |
| Documentation | `/docs/KNOWLEDGE_VAULT.md` |
