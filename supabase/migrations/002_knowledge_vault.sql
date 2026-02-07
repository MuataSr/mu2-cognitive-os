-- ============================================================================
-- Migration 002: The Knowledge Vault
-- Hybrid RAG (Vector + Graph) Database Structures
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Create textbook_chunks table for vector search
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cortex.textbook_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chapter_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    grade_level INTEGER DEFAULT 8,
    subject TEXT DEFAULT 'science',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create HNSW index for fast approximate cosine similarity search
CREATE INDEX IF NOT EXISTS idx_textbook_embeddings
ON cortex.textbook_chunks
USING hnsw (embedding vector_cosine_ops);

-- Additional indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_textbook_chapters ON cortex.textbook_chunks(chapter_id);
CREATE INDEX IF NOT EXISTS idx_textbook_sections ON cortex.textbook_chunks(section_id);
CREATE INDEX IF NOT EXISTS idx_textbook_grade_subject ON cortex.textbook_chunks(grade_level, subject);
CREATE INDEX IF NOT EXISTS idx_textbook_metadata ON cortex.textbook_chunks USING gin (metadata);

-- ----------------------------------------------------------------------------
-- 2. Create graph_nodes and graph_edges tables to complement Apache AGE
-- These provide relational views while AGE handles graph queries
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cortex.graph_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    graph_name TEXT NOT NULL DEFAULT 'kda_curriculum',
    node_id BIGINT,
    label TEXT NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(graph_name, node_id)
);

CREATE TABLE IF NOT EXISTS cortex.graph_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    graph_name TEXT NOT NULL DEFAULT 'kda_curriculum',
    edge_id BIGINT,
    start_node_id BIGINT NOT NULL,
    end_node_id BIGINT NOT NULL,
    edge_label TEXT NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(graph_name, edge_id)
);

-- Indexes for graph tables
CREATE INDEX IF NOT EXISTS idx_graph_nodes_label ON cortex.graph_nodes(label);
CREATE INDEX IF NOT EXISTS idx_graph_edges_label ON cortex.graph_edges(edge_label);
CREATE INDEX IF NOT EXISTS idx_graph_edges_start ON cortex.graph_edges(start_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_end ON cortex.graph_edges(end_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_properties ON cortex.graph_nodes USING gin (properties);
CREATE INDEX IF NOT EXISTS idx_graph_edges_properties ON cortex.graph_edges USING gin (properties);

-- ----------------------------------------------------------------------------
-- 3. Create junction table for chunk-to-node relationships
-- Links textbook content to graph concepts
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cortex.chunk_concept_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID NOT NULL REFERENCES cortex.textbook_chunks(id) ON DELETE CASCADE,
    node_id BIGINT NOT NULL,
    relevance_score FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunk_concept_chunk ON cortex.chunk_concept_links(chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunk_concept_node ON cortex.chunk_concept_links(node_id);

-- ----------------------------------------------------------------------------
-- 4. Enable Row Level Security
-- ----------------------------------------------------------------------------
ALTER TABLE cortex.textbook_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE cortex.graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE cortex.graph_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE cortex.chunk_concept_links ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- 5. RLS Policies
-- ----------------------------------------------------------------------------

-- Textbook chunks: Students can read, instructors/admins can write
CREATE POLICY "Students can view textbook chunks"
ON cortex.textbook_chunks FOR SELECT
TO authenticated
USING (
    auth.jwt() ->> 'role' IN ('student', 'instructor', 'admin')
);

CREATE POLICY "Instructors can insert textbook chunks"
ON cortex.textbook_chunks FOR INSERT
TO authenticated
WITH CHECK (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
);

CREATE POLICY "Instructors can update textbook chunks"
ON cortex.textbook_chunks FOR UPDATE
TO authenticated
USING (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
)
WITH CHECK (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
);

CREATE POLICY "Admins can delete textbook chunks"
ON cortex.textbook_chunks FOR DELETE
TO authenticated
USING (
    auth.jwt() ->> 'role' = 'admin'
);

-- Graph nodes: Read-only for students, write for instructors/admins
CREATE POLICY "Students can view graph nodes"
ON cortex.graph_nodes FOR SELECT
TO authenticated
USING (
    auth.jwt() ->> 'role' IN ('student', 'instructor', 'admin')
);

CREATE POLICY "Instructors can manage graph nodes"
ON cortex.graph_nodes FOR ALL
TO authenticated
USING (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
)
WITH CHECK (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
);

-- Graph edges: Same as nodes
CREATE POLICY "Students can view graph edges"
ON cortex.graph_edges FOR SELECT
TO authenticated
USING (
    auth.jwt() ->> 'role' IN ('student', 'instructor', 'admin')
);

CREATE POLICY "Instructors can manage graph edges"
ON cortex.graph_edges FOR ALL
TO authenticated
USING (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
)
WITH CHECK (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
);

-- Chunk-concept links: Same access pattern
CREATE POLICY "Students can view chunk-concept links"
ON cortex.chunk_concept_links FOR SELECT
TO authenticated
USING (
    auth.jwt() ->> 'role' IN ('student', 'instructor', 'admin')
);

CREATE POLICY "Instructors can manage chunk-concept links"
ON cortex.chunk_concept_links FOR ALL
TO authenticated
USING (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
)
WITH CHECK (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
);

-- ----------------------------------------------------------------------------
-- 6. Helper Functions for Hybrid RAG
-- ----------------------------------------------------------------------------

-- Function to perform vector similarity search on textbook chunks
CREATE OR REPLACE FUNCTION cortex.search_similar_chunks(
    query_embedding vector(1536),
    p_grade_level INTEGER DEFAULT NULL,
    p_subject TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 10,
    p_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    chapter_id TEXT,
    section_id TEXT,
    content TEXT,
    grade_level INTEGER,
    subject TEXT,
    metadata JSONB,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        tc.id,
        tc.chapter_id,
        tc.section_id,
        tc.content,
        tc.grade_level,
        tc.subject,
        tc.metadata,
        1 - (tc.embedding <=> query_embedding) as similarity
    FROM cortex.textbook_chunks tc
    WHERE
        (p_grade_level IS NULL OR tc.grade_level = p_grade_level)
        AND (p_subject IS NULL OR tc.subject = p_subject)
        AND tc.embedding IS NOT NULL
        AND (1 - (tc.embedding <=> query_embedding)) >= p_threshold
    ORDER BY tc.embedding <=> query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute on search function
GRANT EXECUTE ON FUNCTION cortex.search_similar_chunks TO authenticated;

-- Function to get concept context from graph
CREATE OR REPLACE FUNCTION cortex.get_concept_context(
    concept_label TEXT
)
RETURNS TABLE (
    related_concept TEXT,
    relationship_type TEXT,
    direction TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(end_node.label, start_node.label) as related_concept,
        edge.edge_label as relationship_type,
        CASE
            WHEN start_node.label = concept_label THEN 'outgoing'
            ELSE 'incoming'
        END as direction
    FROM cortex.graph_edges edge
    JOIN cortex.graph_nodes start_node ON edge.start_node_id = start_node.node_id
    JOIN cortex.graph_nodes end_node ON edge.end_node_id = end_node.node_id
    WHERE
        start_node.label = concept_label
        OR end_node.label = concept_label;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute on context function
GRANT EXECUTE ON FUNCTION cortex.get_concept_context TO authenticated;

-- ----------------------------------------------------------------------------
-- 7. Views for common queries
-- ----------------------------------------------------------------------------

-- View for chunks with related concepts
CREATE OR REPLACE VIEW cortex.chunk_with_concepts AS
SELECT
    tc.id,
    tc.chapter_id,
    tc.section_id,
    tc.content,
    tc.grade_level,
    tc.subject,
    tc.metadata,
    tc.created_at,
    json_agg(
        json_build_object(
            'node_id', gn.node_id,
            'label', gn.label,
            'properties', gn.properties,
            'relevance', ccl.relevance_score
        )
    ) FILTER (WHERE gn.node_id IS NOT NULL) as related_concepts
FROM cortex.textbook_chunks tc
LEFT JOIN cortex.chunk_concept_links ccl ON tc.id = ccl.chunk_id
LEFT JOIN cortex.graph_nodes gn ON ccl.node_id = gn.node_id
GROUP BY tc.id;

-- View for graph statistics
CREATE OR REPLACE VIEW cortex.graph_statistics AS
SELECT
    graph_name,
    COUNT(DISTINCT node_id) as node_count,
    COUNT(DISTINCT edge_id) as edge_count,
    COUNT(DISTINCT label) as unique_labels
FROM cortex.graph_nodes
GROUP BY graph_name;

-- ----------------------------------------------------------------------------
-- 8. Comments for documentation
-- ----------------------------------------------------------------------------

COMMENT ON TABLE cortex.textbook_chunks IS 'Stores textbook content chunks with embeddings for semantic search';
COMMENT ON TABLE cortex.graph_nodes IS 'Relational mirror of Apache AGE graph nodes for kda_curriculum';
COMMENT ON TABLE cortex.graph_edges IS 'Relational mirror of Apache AGE graph edges for kda_curriculum';
COMMENT ON TABLE cortex.chunk_concept_links IS 'Links textbook chunks to graph concepts for hybrid retrieval';
COMMENT ON FUNCTION cortex.search_similar_chunks IS 'Performs vector similarity search on textbook chunks with optional filters';
COMMENT ON FUNCTION cortex.get_concept_context IS 'Retrieves related concepts and relationships for a given concept';
