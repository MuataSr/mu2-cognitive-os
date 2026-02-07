# Knowledge Vault - Architecture Diagrams

**Visual documentation of the Hybrid RAG system architecture.**

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MU2 COGNITIVE OS                                   │
│                         Knowledge Vault (Sprint 2)                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────┐         ┌────────────────┐         ┌────────────────┐
│   Brain API    │         │  Supabase API  │         │   Auth/RLS     │
│   (FastAPI)    │◄────────┤    (REST)      │◄────────┤   (GoTrue)     │
│                │         │                │         │                │
│ • LlamaIndex   │         │ • PostgREST    │         │ • JWT tokens   │
│ • LangGraph    │         │ • Realtime     │         │ • Role checks  │
└────────────────┘         └────────────────┘         └────────────────┘
         │                           │
         └───────────────┬───────────┘
                         ▼
         ┌──────────────────────────────────────┐
         │     PostgreSQL 15 Database           │
         │         (localhost:54322)            │
         ├──────────────────────────────────────┤
         │                                      │
         │  ┌────────────────────────────────┐  │
         │  │       cortex schema            │  │
         │  ├────────────────────────────────┤  │
         │  │ • textbook_chunks (vector)     │  │
         │  │ • graph_nodes (mirror)         │  │
         │  │ • graph_edges (mirror)         │  │
         │  │ • chunk_concept_links          │  │
         │  │ • user_sessions                │  │
         │  └────────────────────────────────┘  │
         │                                      │
         │  ┌────────────────────────────────┐  │
         │  │       Extensions               │  │
         │  ├────────────────────────────────┤  │
         │  │ • pgvector (vector search)     │  │
         │  │ • age (graph database)         │  │
         │  │ • uuid-ossp                    │  │
         │  └────────────────────────────────┘  │
         └──────────────────────────────────────┘
```

## Hybrid RAG Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HYBRID RAG QUERY FLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

User Query
    │
    ▼
┌───────────────┐
│ Embedding     │ ◄─── Ollama (nomic-embed-text)
│ Generation    │
└───────┬───────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PARALLEL SEARCH                        │
├─────────────────────────────┬───────────────────────────────────┤
│                                                             │
│   VECTOR SEARCH (pgvector)    │    GRAPH TRAVERSAL (Apache AGE) │
│                                                             │
│   ┌───────────────────┐      │    ┌───────────────────┐      │
│   │ textbook_chunks   │      │    │  kda_curriculum   │      │
│   │                   │      │    │      Graph        │      │
│   │ • HNSW Index      │      │    │                   │      │
│   │ • Cosine Similar. │      │    │ • Concepts        │      │
│   │ • Top-K Results   │      │    │ • Relationships   │      │
│   └───────────────────┘      │    │ • Context Paths   │      │
│          │                  │    └───────────────────┘      │
│          │ Similar Chunks   │              │                 │
│          ▼                  │              │ Related Concepts│
│    ┌──────────┐             │              ▼                 │
│    │  Ranked  │             │       ┌──────────┐            │
│    │  Results │             │       │  Concept │            │
│    └──────────┘             │       │  Context │            │
│                                                             │
└─────────────────────────────┴───────────────────────────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │  Chunk-Concept    │
                              │      Links        │
                              │  (Join Results)   │
                              └─────────┬─────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │   Context         │
                              │   Assembly        │
                              │   (Hybrid RAG)    │
                              └─────────┬─────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │   LLM Generation   │
                              │   (Response)       │
                              └───────────────────┘
```

## Database Schema Detail

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CORTEX SCHEMA STRUCTURE                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ textbook_chunks                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ • id              UUID          PRIMARY KEY                                 │
│ • chapter_id      TEXT          NOT NULL                                    │
│ • section_id      TEXT          NOT NULL                                    │
│ • content         TEXT          NOT NULL                                    │
│ • embedding       vector(1536)  INDEXED (HNSW)                              │
│ • grade_level     INTEGER       DEFAULT 8                                   │
│ • subject         TEXT          DEFAULT 'science'                           │
│ • metadata        JSONB         DEFAULT '{}'                                │
│ • created_at      TIMESTAMPTZ   DEFAULT NOW()                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ Many-to-Many
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ chunk_concept_links                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ • id              UUID          PRIMARY KEY                                 │
│ • chunk_id        UUID          FK → textbook_chunks                        │
│ • node_id         BIGINT        FK → graph_nodes                            │
│ • relevance_score FLOAT         DEFAULT 1.0                                 │
│ • created_at      TIMESTAMPTZ   DEFAULT NOW()                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ▲
                                        │
                                        │ References
                                        │
┌─────────────────────────────────────────────────────────────────────────────┐
│ graph_nodes                                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ • id              UUID          PRIMARY KEY                                 │
│ • graph_name      TEXT          DEFAULT 'kda_curriculum'                    │
│ • node_id         BIGINT        UNIQUE (graph_name, node_id)               │
│ • label           TEXT          NOT NULL                                    │
│ • properties      JSONB         DEFAULT '{}'                                │
│ • created_at      TIMESTAMPTZ   DEFAULT NOW()                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ Mirrors AGE
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Apache AGE: kda_curriculum Graph                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    (Cell) ──[:CONTAINS]──> (Chloroplast) ──[:SITE_OF]──> (Photosynthesis)  │
│       │                                              │                      │
│    [:CONTAINS]                                    [:REQUIRES]              │
│       │                                              │                      │
│       ▼                                              ▼                      │
│   (Nucleus)                                      (Sunlight)                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │
┌─────────────────────────────────────────────────────────────────────────────┐
│ graph_edges                                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ • id              UUID          PRIMARY KEY                                 │
│ • graph_name      TEXT          DEFAULT 'kda_curriculum'                    │
│ • edge_id         BIGINT        UNIQUE (graph_name, edge_id)                │
│ • start_node_id   BIGINT        FK → graph_nodes                            │
│ • end_node_id     BIGINT        FK → graph_nodes                            │
│ • edge_label      TEXT          NOT NULL                                    │
│ • properties      JSONB         DEFAULT '{}'                                │
│ • created_at      TIMESTAMPTZ   DEFAULT NOW()                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Knowledge Graph Ontology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KDA CURRICULUM ONTOLOGY                                  │
└─────────────────────────────────────────────────────────────────────────────┘

BIOLOGY DOMAIN                    PHYSICS DOMAIN
═════════════                     ═════════════

┌──────────────┐                 ┌──────────────┐
│   Cell       │                 │   Energy     │
│              │                 │              │
│ • Nucleus    │                 │ • Kinetic    │
│ • Mitochond. │                 │ • Potential  │
│ • Chloropl.  │                 └──────┬───────┘
│ • Membrane   │                        │
│ • Cytoplasm  │                        ▼
└──────┬───────┘                 ┌──────────────┐
       │                          │    Force     │
       ▼                          │              │
┌──────────────┐                 │ • Gravity    │
│Photosynthesis│                 │ • Motion     │
│              │                 │ • Speed      │
│ [REQUIRES]   │                 │ • Velocity   │
│   Sunlight   │                 │ • Accel.     │
│   CO₂        │                 └──────────────┘
│   H₂O        │
│              │
│ [PRODUCES]   │                 CHEMISTRY DOMAIN
│   Oxygen     │                 ════════════════
│   Glucose    │
└──────┬───────┘                 ┌──────────────┐
       │                          │   Matter     │
       ▼                          │              │
┌──────────────┐                 │ • Atom       │
│  Ecosystem   │                 │ • Element    │
│              │                 │ • Molecule   │
│ • Producer   │                 │ • Compound   │
│ • Consumer   │                 └──────┬───────┘
│ • Decomposer │                        │
│ • Food Chain │                        ▼
└──────────────┘                 ┌──────────────┐
                                 │    Cell      │
                                 │ (Atoms)      │
                                 └──────────────┘

EARTH SCIENCE DOMAIN
═════════════════════

┌──────────────┐
│ Water Cycle  │
│              │
│ • Evaporate  │
│ • Condense   │
│ • Precipitate│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Weather      │─────┐
│              │     │
└──────────────┘     ▼
              ┌──────────────┐
              │   Climate    │
              └──────────────┘

┌──────────────┐
│Plate Tectonics│
│              │
│ • Earthquake │
│ • Volcano    │
└──────────────┘

CROSS-DOMAIN CONNECTIONS:
═══════════════════════════
• Cell MADE_OF Atom
• Sunlight IS Energy
• Photosynthesis TRANSFORMS Energy
• Gravity AFFECTS Water
```

## Security Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ROW LEVEL SECURITY (RLS) MODEL                           │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   Auth Request   │
                    │   (JWT Token)    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   GoTrue Auth    │
                    │   Validate JWT   │
                    └────────┬─────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
         ┌───────────┐              ┌───────────┐
         │ Student   │              │ Instructor │
         │ role:     │              │ role:      │
         │ "student" │              │ "instructor"│
         └─────┬─────┘              └─────┬─────┘
               │                          │
               ▼                          ▼
    ┌───────────────────┐        ┌───────────────────┐
    │ READ-ONLY Access  │        │ READ/WRITE Access │
    ├───────────────────┤        ├───────────────────┤
    │ • SELECT chunks   │        │ • SELECT chunks   │
    │ • SELECT nodes    │        │ • INSERT chunks   │
    │ • SELECT edges    │        │ • UPDATE chunks   │
    │ • SELECT links    │        │ • DELETE chunks   │
    │                   │        │ • Manage graph    │
    └───────────────────┘        └───────────────────┘
                                        │
                                        ▼
                                 ┌───────────┐
                                 │   Admin    │
                                 │ role:      │
                                 │ "admin"    │
                                 └─────┬─────┘
                                       │
                                       ▼
                               ┌───────────────────┐
                               │  FULL ACCESS      │
                               │  + Delete Rights  │
                               └───────────────────┘

Policy Examples:
═════════════════

-- Student read-only
CREATE POLICY "Students can view textbook chunks"
ON cortex.textbook_chunks FOR SELECT
TO authenticated
USING (auth.jwt() ->> 'role' IN ('student', 'instructor', 'admin'));

-- Instructor write
CREATE POLICY "Instructors can insert textbook chunks"
ON cortex.textbook_chunks FOR INSERT
TO authenticated
WITH CHECK (auth.jwt() ->> 'role' IN ('instructor', 'admin'));

-- Admin delete
CREATE POLICY "Admins can delete textbook chunks"
ON cortex.textbook_chunks FOR DELETE
TO authenticated
USING (auth.jwt() ->> 'role' = 'admin');
```

## Index Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATABASE INDEXES                                   │
└─────────────────────────────────────────────────────────────────────────────┘

textbook_chunks:
├─ idx_textbook_embeddings     (HNSW, vector_cosine_ops)
├─ idx_textbook_chapters       (B-tree, chapter_id)
├─ idx_textbook_sections       (B-tree, section_id)
├─ idx_textbook_grade_subject  (B-tree, grade_level, subject)
└─ idx_textbook_metadata       (GIN, metadata)

graph_nodes:
├─ idx_graph_nodes_label       (B-tree, label)
└─ idx_graph_nodes_properties  (GIN, properties)

graph_edges:
├─ idx_graph_edges_label       (B-tree, edge_label)
├─ idx_graph_edges_start       (B-tree, start_node_id)
├─ idx_graph_edges_end         (B-tree, end_node_id)
└─ idx_graph_edges_properties  (GIN, properties)

chunk_concept_links:
├─ idx_chunk_concept_chunk     (B-tree, chunk_id)
└─ idx_chunk_concept_node      (B-tree, node_id)

user_sessions:
├─ idx_user_sessions_user_id   (B-tree, user_id)
└─ idx_user_sessions_session_start (B-tree, session_start DESC)
```
