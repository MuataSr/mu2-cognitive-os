-- Create textbook_chunks table with vector support
CREATE TABLE IF NOT EXISTS cortex.textbook_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    grade_level INTEGER DEFAULT 8,
    subject TEXT DEFAULT 'science',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_textbook_embeddings
ON cortex.textbook_chunks
USING hnsw (embedding vector_cosine_ops);

-- Grant permissions
GRANT USAGE ON SCHEMA cortex, vectordb TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA cortex TO PUBLIC;
