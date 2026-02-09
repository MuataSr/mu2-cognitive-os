-- OpenStax Textbook Chunks with Embeddings
-- Stores vector embeddings for semantic search

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create textbook chunks table
CREATE TABLE IF NOT EXISTS textbook_chunks (
    id BIGSERIAL PRIMARY KEY,
    chunk_id TEXT UNIQUE NOT NULL,
    chapter_id TEXT NOT NULL,
    book_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL,
    embedding vector(768),  -- embeddinggemma:300m dimension
    word_count INTEGER NOT NULL,
    key_concepts JSONB DEFAULT '[]'::jsonb,
    definitions JSONB DEFAULT '{}'::jsonb,
    section_title TEXT,
    source_location TEXT,

    -- Metadata
    embedding_model TEXT NOT NULL DEFAULT 'embeddinggemma:300m',
    embedding_dimension INTEGER NOT NULL DEFAULT 768,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for vector similarity search
CREATE INDEX IF NOT EXISTS idx_textbook_chunks_embedding
    ON textbook_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Create indexes for filtering
CREATE INDEX IF NOT EXISTS idx_textbook_chunks_book_id ON textbook_chunks(book_id);
CREATE INDEX IF NOT EXISTS idx_textbook_chunks_chapter_id ON textbook_chunks(chapter_id);
CREATE INDEX IF NOT EXISTS idx_textbook_chunks_content_type ON textbook_chunks(content_type);

-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_textbook_chunks_updated_at
    BEFORE UPDATE ON textbook_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON TABLE textbook_chunks IS 'Stores OpenStax textbook chunks with vector embeddings for semantic search';
COMMENT ON COLUMN textbook_chunks.embedding IS '768-dimensional vector from embeddinggemma:300m model';
COMMENT ON COLUMN textbook_chunks.key_concepts IS 'List of key concepts extracted from the chunk';
COMMENT ON COLUMN textbook_chunks.definitions IS 'Dictionary of term -> definition mappings';
