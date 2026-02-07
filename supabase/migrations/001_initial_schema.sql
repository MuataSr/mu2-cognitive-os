-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgvector" CASCADE;
CREATE EXTENSION IF NOT EXISTS "age" CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" CASCADE;
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" CASCADE;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS cortex;
CREATE SCHEMA IF NOT EXISTS vectordb;

-- Grant permissions
GRANT USAGE ON SCHEMA cortex, vectordb TO postgres, anon, authenticated, service_role;

-- Create table for cognitive state tracking
CREATE TABLE cortex.user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    session_start TIMESTAMPTZ DEFAULT NOW(),
    session_end TIMESTAMPTZ,
    current_mode TEXT DEFAULT 'standard',
    focus_level INTEGER DEFAULT 50,
    context_vector vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create table for knowledge retrieval
CREATE TABLE vectordb.knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    chunk_type TEXT NOT NULL,
    source TEXT,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector index for similarity search
CREATE INDEX idx_knowledge_chunks_embedding ON vectordb.knowledge_chunks
USING hnsw (embedding vector_cosine_ops);

-- Create indexes
CREATE INDEX idx_user_sessions_user_id ON cortex.user_sessions(user_id);
CREATE INDEX idx_user_sessions_session_start ON cortex.user_sessions(session_start DESC);

-- Enable Row Level Security
ALTER TABLE cortex.user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE vectordb.knowledge_chunks ENABLE ROW LEVEL SECURITY;

-- Create functions for updated_at
CREATE OR REPLACE FUNCTION cortex.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_sessions_updated_at
    BEFORE UPDATE ON cortex.user_sessions
    FOR EACH ROW
    EXECUTE FUNCTION cortex.update_updated_at();

-- Create view for session summary
CREATE OR REPLACE VIEW cortex.active_sessions AS
SELECT
    id,
    user_id,
    session_start,
    current_mode,
    focus_level,
    EXTRACT(EPOCH FROM (NOW() - session_start))/60 as duration_minutes
FROM cortex.user_sessions
WHERE session_end IS NULL;
