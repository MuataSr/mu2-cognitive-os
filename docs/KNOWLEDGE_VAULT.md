# Knowledge Vault - Hybrid RAG Database

**Sprint 2, Task 2.1 | The Mu2 Cognitive OS Project**

## Overview

The Knowledge Vault is a Hybrid RAG (Retrieval-Augmented Generation) system combining:
- **Vector Search** via pgvector for semantic similarity
- **Graph Database** via Apache AGE for knowledge relationships
- **Row-Level Security** for FERPA-compliant access control

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Knowledge Vault                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │  Vector Search   │         │  Graph Database  │              │
│  │  (pgvector)      │◄────────┤  (Apache AGE)    │              │
│  │                  │         │                  │              │
│  │ • HNSW Index     │         │ • kda_curriculum │              │
│  │ • Cosine Similarity│       │ • Concepts/Edges │              │
│  │ • 1536 dims      │         │ • Cypher Queries │              │
│  └──────────────────┘         └──────────────────┘              │
│           │                            │                         │
│           └────────────┬───────────────┘                         │
│                        ▼                                         │
│              ┌──────────────────┐                               │
│              │  Chunk-Concept   │                               │
│              │      Links       │                               │
│              └──────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

## Database Schema

### 1. Textbook Chunks (Vector Store)

**Table:** `cortex.textbook_chunks`

Stores textbook content with vector embeddings for semantic search.

```sql
CREATE TABLE cortex.textbook_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chapter_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),           -- OpenAI/Ollama compatible
    grade_level INTEGER DEFAULT 8,
    subject TEXT DEFAULT 'science',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Index:** HNSW (Hierarchical Navigable Small World)
```sql
CREATE INDEX idx_textbook_embeddings
ON cortex.textbook_chunks
USING hnsw (embedding vector_cosine_ops);
```

### 2. Graph Structures (Apache AGE)

**Graph Name:** `kda_curriculum`

**Relational Mirrors:**
- `cortex.graph_nodes` - Node data
- `cortex.graph_edges` - Edge data
- `cortex.chunk_concept_links` - Links chunks to graph concepts

**Sample Ontology:**
```
(Cell)-[:CONTAINS]->(Chloroplast)-[:SITE_OF]->(Photosynthesis)
                                   ↓
                             [:REQUIRES]
                                   ↓
                              (Sunlight)
                                   ↓
                             [:PRODUCES]
                                   ↓
                              (Oxygen)
```

## Features

### Vector Search

**Function:** `cortex.search_similar_chunks()`

```sql
SELECT * FROM cortex.search_similar_chunks(
    query_embedding := '[0.1, 0.2, ...]'::vector(1536),
    p_grade_level := 8,
    p_subject := 'science',
    p_limit := 10,
    p_threshold := 0.7
);
```

Returns similar textbook chunks ranked by cosine similarity.

### Graph Traversal

**Function:** `cortex.get_concept_context()`

```sql
SELECT * FROM cortex.get_concept_context('Photosynthesis');
```

Returns related concepts and their relationships.

### Hybrid RAG

**View:** `cortex.chunk_with_concepts`

Combines vector chunks with their linked graph concepts:

```sql
SELECT
    chapter_id,
    content,
    related_concepts
FROM cortex.chunk_with_concepts
WHERE grade_level = 8
  AND subject = 'science';
```

## Security

### Row-Level Security (RLS)

All tables have RLS enabled with policies:

| Role | textbook_chunks | graph_nodes | graph_edges |
|------|-----------------|-------------|-------------|
| **student** | READ | READ | READ |
| **instructor** | READ/WRITE | READ/WRITE | READ/WRITE |
| **admin** | READ/WRITE/DELETE | READ/WRITE | READ/WRITE |

### Policy Examples

```sql
-- Students can view textbook chunks
CREATE POLICY "Students can view textbook chunks"
ON cortex.textbook_chunks FOR SELECT
TO authenticated
USING (auth.jwt() ->> 'role' IN ('student', 'instructor', 'admin'));

-- Only admins can delete
CREATE POLICY "Admins can delete textbook chunks"
ON cortex.textbook_chunks FOR DELETE
TO authenticated
USING (auth.jwt() ->> 'role' = 'admin');
```

## Knowledge Graph Ontology

### Science Domains Covered

#### Biology (8th Grade)
- **Cell Structure:** Cell, Nucleus, Mitochondria, Chloroplast, Cell Membrane
- **Photosynthesis:** Process, inputs (Sunlight, CO₂, H₂O), outputs (O₂, Glucose)
- **Ecosystems:** Producers, Consumers, Decomposers, Food Chains

#### Physics (8th Grade)
- **Energy:** Kinetic, Potential
- **Forces:** Gravity, Motion, Speed, Velocity, Acceleration

#### Chemistry (8th Grade)
- **Matter:** Atoms, Elements, Molecules, Compounds
- **Atomic Structure:** Protons, Neutrons, Electrons

#### Earth Science (8th Grade)
- **Water Cycle:** Evaporation, Condensation, Precipitation
- **Plate Tectonics:** Earthquakes, Volcanoes
- **Weather vs Climate**

### Relationship Types

| Type | Description | Example |
|------|-------------|---------|
| `CONTAINS` | Part-whole | Cell CONTAINS Nucleus |
| `REQUIRES` | Dependency | Photosynthesis REQUIRES Sunlight |
| `PRODUCES` | Output | Photosynthesis PRODUCES Oxygen |
| `CAUSES` | Causality | Force CAUSES Motion |
| `MADE_OF` | Composition | Matter MADE_OF Atoms |

## Installation & Setup

### Prerequisites

1. **Docker** running with containers up:
   ```bash
   cd /home/papi/Documents/mu2-cognitive-os
   docker-compose up -d
   ```

2. **Database** accessible on port 54322

### Quick Start

1. **Initialize the Knowledge Vault:**
   ```bash
   ./supabase/scripts/init_knowledge_vault.sh
   ```

   This script:
   - Checks database connectivity
   - Runs migrations (001, 002)
   - Creates Apache AGE graph
   - Seeds graph data
   - Runs tests

2. **Verify Installation:**
   ```bash
   psql -h localhost -p 54322 -U postgres -d postgres \
     -f supabase/tests/test_knowledge_vault.sql
   ```

### Manual Setup

If you prefer manual setup:

```bash
# 1. Run migrations
psql -h localhost -p 54322 -U postgres -d postgres \
  -f supabase/migrations/001_initial_schema.sql

psql -h localhost -p 54322 -U postgres -d postgres \
  -f supabase/migrations/002_knowledge_vault.sql

# 2. Initialize AGE graph
psql -h localhost -p 54322 -U postgres -d postgres
```

```sql
-- In psql
LOAD 'age';
SELECT create_graph('kda_curriculum');
```

```bash
# 3. Seed graph data
psql -h localhost -p 54322 -U postgres -d postgres \
  -f supabase/migrations/seed_graph.sql

# 4. Run tests
psql -h localhost -p 54322 -U postgres -d postgres \
  -f supabase/tests/test_knowledge_vault.sql
```

## Usage Examples

### Example 1: Vector Search for Similar Content

```sql
-- Find textbook chunks similar to a query about photosynthesis
WITH query AS (
    SELECT '[0.1, 0.2, 0.3, ...]'::vector(1536) as embedding
)
SELECT
    chapter_id,
    section_id,
    LEFT(content, 100) as content_preview,
    similarity
FROM cortex.search_similar_chunks(
    (SELECT embedding FROM query),
    8,  -- grade_level
    'science',
    5,  -- limit
    0.7 -- threshold
);
```

### Example 2: Graph Traversal - Photosynthesis Context

```sql
-- Get all concepts related to Photosynthesis
SELECT
    related_concept,
    relationship_type,
    direction
FROM cortex.get_concept_context('Photosynthesis');
```

**Expected Output:**
```
   related_concept   | relationship_type | direction
---------------------+-------------------+-----------
 Sunlight            | REQUIRES          | outgoing
 Carbon Dioxide      | USES              | outgoing
 Water               | USES              | outgoing
 Oxygen              | PRODUCES          | outgoing
 Glucose             | PRODUCES          | outgoing
 Chloroplast         | SITE_OF           | incoming
```

### Example 3: Hybrid Query - Chunks with Concepts

```sql
-- Find chunks about biology with their linked concepts
SELECT
    chapter_id,
    section_id,
    LEFT(content, 80) as preview,
    jsonb_array_elements(related_concepts)->>'label' as concept
FROM cortex.chunk_with_concepts
WHERE grade_level = 8
  AND subject = 'science'
  AND related_concepts IS NOT NULL;
```

### Example 4: Cross-Domain Knowledge Discovery

```sql
-- Find connections between biology and chemistry
SELECT DISTINCT
    n1.label as concept1,
    e.edge_label as relationship,
    n2.label as concept2,
    n1.properties->>'domain' as domain1,
    n2.properties->>'domain' as domain2
FROM cortex.graph_edges e
JOIN cortex.graph_nodes n1 ON e.start_node_id = n1.node_id
JOIN cortex.graph_nodes n2 ON e.end_node_id = n2.node_id
WHERE n1.properties->>'domain' != n2.properties->>'domain';
```

### Example 5: Graph Statistics

```sql
-- View curriculum coverage by domain
SELECT * FROM cortex.curriculum_graph_stats;
```

**Expected Output:**
```
    domain     | concept_count | sample_concepts
---------------+---------------+-----------------
 Biology       |            25 | {Cell,Photosyn...}
 Physics       |            10 | {Energy,Force...}
 Chemistry     |             8 | {Atom,Molecule...}
 Earth Science |            10 | {Water Cycle...}
```

## API Integration

The Knowledge Vault is designed to work with the Brain API (FastAPI) in `/packages/brain`:

### Vector Embedding Flow

```python
# In Brain API
from ollama import embeddings

# Generate embedding for query
query = "How does photosynthesis work?"
emb = embeddings(model='nomic-embed-text', prompt=query)

# Search similar chunks
results = cortex.search_similar_chunks(
    embedding=emb['embedding'],
    grade_level=8,
    subject='science'
)
```

### Graph Context Flow

```python
# Get concept context
concepts = cortex.get_concept_context('Photosynthesis')

# Build knowledge graph for RAG
context = build_rag_context(
    vector_results=results,
    graph_context=concepts
)
```

## File Structure

```
supabase/
├── migrations/
│   ├── 001_initial_schema.sql       # Base schema (user_sessions, etc.)
│   ├── 002_knowledge_vault.sql      # Knowledge Vault tables & RLS
│   └── seed_graph.sql               # Science concepts ontology
├── tests/
│   └── test_knowledge_vault.sql     # Test suite
├── scripts/
│   └── init_knowledge_vault.sh      # Initialization script
└── extensions/
    └── (Apache AGE shared objects)
```

## Performance Considerations

### Vector Search
- **HNSW Index:** ~O(log n) search complexity
- **Dimensions:** 1536 (OpenAI/Ollama compatible)
- **Distance Metric:** Cosine similarity (vector_cosine_ops)
- **Recommended:** Keep embedding vectors normalized

### Graph Queries
- **AGE Cypher:** Optimized for traversals
- **Relational Mirrors:** Use for simple lookups
- **Complex Traversals:** Use AGE directly via Cypher

### Optimization Tips
1. **Batch insertions** for better performance
2. **Use materialized views** for frequent complex queries
3. **Monitor index usage** with `EXPLAIN ANALYZE`
4. **Connection pooling** via PgBouncer recommended

## Troubleshooting

### Issue: "extension age not found"
**Solution:** Ensure pgvector and apache_age are in `shared_preload_libraries` in `postgresql.conf`

### Issue: "vector(1536) type does not exist"
**Solution:** Run `CREATE EXTENSION pgvector CASCADE;`

### Issue: Graph queries return empty
**Solution:** Verify AGE graph exists:
```sql
SELECT graphname FROM ag_graph WHERE graphname = 'kda_curriculum';
```

### Issue: RLS blocking access
**Solution:** Check JWT token contains 'role' claim:
```sql
SELECT auth.jwt();
```

## Compliance & Security

### FERPA Compliance
- All data access logged via RLS
- Student data isolated by user_id
- No PII in textbook content
- Read-only access for students

### Data Privacy
- No cloud services (localhost only)
- No external API calls
- All embeddings generated locally via Ollama
- Row-level security enforced at database level

## Future Enhancements

- [ ] Add more domains (History, Literature)
- [ ] Implement graph-based recommendation
- [ ] Add temporal knowledge (concept prerequisites)
- [ ] Multi-language support
- [ ] Concept difficulty ranking
- [ ] Learning path generation via graph

## References

- **pgvector:** https://github.com/pgvector/pgvector
- **Apache AGE:** https://age.apache.org/
- **Supabase:** https://supabase.com/docs
- **RAG:** https://arxiv.org/abs/2005.11401

---

**Status:** ✅ COMPLETE - Sprint 2, Task 2.1

**Last Updated:** 2026-02-07

**Author:** Architect (Infrastructure & Database Lead)
