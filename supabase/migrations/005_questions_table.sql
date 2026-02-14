-- ============================================================================
-- Migration 005: Questions Table
-- Stores imported questions from SciQ, National Science Bowl, and other sources
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Create questions table with pgvector support
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cortex.questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id TEXT NOT NULL,  -- External ID (e.g., "sciq_12345")
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL,  -- 'multiple_choice', 'true_false', 'short_answer'
    subject TEXT NOT NULL,  -- 'Physics', 'Chemistry', 'Biology', 'Math', etc.
    topic TEXT,  -- e.g., 'Photosynthesis', 'Newton Laws'
    difficulty TEXT DEFAULT 'medium',  -- 'easy', 'medium', 'hard'
    grade_level INTEGER DEFAULT 8,  -- Appropriate grade level

    -- Answer fields
    correct_answer TEXT NOT NULL,
    incorrect_answers TEXT[],  -- Array of wrong options
    explanation TEXT,  -- Optional explanation

    -- Distractors (for SciQ dataset)
    distractor1 TEXT,
    distractor2 TEXT,
    distractor3 TEXT,

    -- Embedding for semantic search (768-dim for nomic-embed-text)
    embedding vector(768),

    -- Metadata
    source TEXT NOT NULL,  -- 'sciq', 'science_bowl', 'opentdb', etc.
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(question_id, source)
);

-- ----------------------------------------------------------------------------
-- 2. Create indexes for fast lookup and vector search
-- ----------------------------------------------------------------------------

-- HNSW index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_questions_embedding
ON cortex.questions
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Subject and topic indexes
CREATE INDEX IF NOT EXISTS idx_questions_subject ON cortex.questions(subject);
CREATE INDEX IF NOT EXISTS idx_questions_topic ON cortex.questions(topic);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON cortex.questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_questions_source ON cortex.questions(source);

-- Composite index for common filters
CREATE INDEX IF NOT EXISTS idx_questions_subject_difficulty
ON cortex.questions(subject, difficulty);

-- GIN index for metadata queries
CREATE INDEX IF NOT EXISTS idx_questions_metadata
ON cortex.questions USING gin (metadata);

-- ----------------------------------------------------------------------------
-- 3. Enable Row Level Security
-- ----------------------------------------------------------------------------
ALTER TABLE cortex.questions ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- 4. RLS Policies
-- ----------------------------------------------------------------------------

-- Students can view questions
CREATE POLICY "Students can view questions"
ON cortex.questions FOR SELECT
TO authenticated
USING (
    auth.jwt() ->> 'role' IN ('student', 'instructor', 'admin')
);

-- Instructors can insert questions
CREATE POLICY "Instructors can insert questions"
ON cortex.questions FOR INSERT
TO authenticated
WITH CHECK (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
);

-- Instructors can update questions
CREATE POLICY "Instructors can update questions"
ON cortex.questions FOR UPDATE
TO authenticated
USING (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
)
WITH CHECK (
    auth.jwt() ->> 'role' IN ('instructor', 'admin')
);

-- Admins can delete questions
CREATE POLICY "Admins can delete questions"
ON cortex.questions FOR DELETE
TO authenticated
USING (
    auth.jwt() ->> 'role' = 'admin'
);

-- ----------------------------------------------------------------------------
-- 5. Helper Functions
-- ----------------------------------------------------------------------------

-- Function to search for similar questions by semantic similarity
CREATE OR REPLACE FUNCTION cortex.search_similar_questions(
    query_embedding vector(768),
    p_subject TEXT DEFAULT NULL,
    p_topic TEXT DEFAULT NULL,
    p_difficulty TEXT DEFAULT NULL,
    p_source TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 10,
    p_threshold FLOAT DEFAULT 0.6
)
RETURNS TABLE (
    id UUID,
    question_id TEXT,
    question_text TEXT,
    question_type TEXT,
    subject TEXT,
    topic TEXT,
    difficulty TEXT,
    correct_answer TEXT,
    incorrect_answers TEXT[],
    explanation TEXT,
    source TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        q.id,
        q.question_id,
        q.question_text,
        q.question_type,
        q.subject,
        q.topic,
        q.difficulty,
        q.correct_answer,
        q.incorrect_answers,
        q.explanation,
        q.source,
        1 - (q.embedding <=> query_embedding) as similarity
    FROM cortex.questions q
    WHERE
        (p_subject IS NULL OR q.subject = p_subject)
        AND (p_topic IS NULL OR q.topic = p_topic)
        AND (p_difficulty IS NULL OR q.difficulty = p_difficulty)
        AND (p_source IS NULL OR q.source = p_source)
        AND q.embedding IS NOT NULL
        AND (1 - (q.embedding <=> query_embedding)) >= p_threshold
    ORDER BY q.embedding <=> query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute on search function
GRANT EXECUTE ON FUNCTION cortex.search_similar_questions TO authenticated;

-- Function to get random questions (for quizzes)
CREATE OR REPLACE FUNCTION cortex.get_random_questions(
    p_subject TEXT DEFAULT NULL,
    p_topic TEXT DEFAULT NULL,
    p_difficulty TEXT DEFAULT NULL,
    p_source TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    question_id TEXT,
    question_text TEXT,
    question_type TEXT,
    subject TEXT,
    topic TEXT,
    difficulty TEXT,
    correct_answer TEXT,
    incorrect_answers TEXT[],
    explanation TEXT,
    source TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        q.id,
        q.question_id,
        q.question_text,
        q.question_type,
        q.subject,
        q.topic,
        q.difficulty,
        q.correct_answer,
        q.incorrect_answers,
        q.explanation,
        q.source
    FROM cortex.questions q
    WHERE
        (p_subject IS NULL OR q.subject = p_subject)
        AND (p_topic IS NULL OR q.topic = p_topic)
        AND (p_difficulty IS NULL OR q.difficulty = p_difficulty)
        AND (p_source IS NULL OR q.source = p_source)
    ORDER BY RANDOM()
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute on random questions function
GRANT EXECUTE ON FUNCTION cortex.get_random_questions TO authenticated;

-- Function to get question statistics
CREATE OR REPLACE FUNCTION cortex.get_question_statistics()
RETURNS TABLE (
    source TEXT,
    subject TEXT,
    total_questions BIGINT,
    easy_count BIGINT,
    medium_count BIGINT,
    hard_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        q.source,
        q.subject,
        COUNT(*) as total_questions,
        SUM(CASE WHEN q.difficulty = 'easy' THEN 1 ELSE 0 END) as easy_count,
        SUM(CASE WHEN q.difficulty = 'medium' THEN 1 ELSE 0 END) as medium_count,
        SUM(CASE WHEN q.difficulty = 'hard' THEN 1 ELSE 0 END) as hard_count
    FROM cortex.questions q
    GROUP BY q.source, q.subject
    ORDER BY q.source, q.subject;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute on statistics function
GRANT EXECUTE ON FUNCTION cortex.get_question_statistics TO authenticated;

-- ----------------------------------------------------------------------------
-- 6. Trigger for updated_at
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cortex.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_questions_updated_at
BEFORE UPDATE ON cortex.questions
FOR EACH ROW
EXECUTE FUNCTION cortex.update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 7. Comments for documentation
-- ----------------------------------------------------------------------------
COMMENT ON TABLE cortex.questions IS 'Stores STEM questions from various sources (SciQ, Science Bowl, OpenTDB) with embeddings for semantic search';
COMMENT ON FUNCTION cortex.search_similar_questions IS 'Performs semantic vector search on questions with optional filters';
COMMENT ON FUNCTION cortex.get_random_questions IS 'Returns random questions filtered by subject/topic/difficulty - useful for quizzes';
COMMENT ON FUNCTION cortex.get_question_statistics IS 'Returns aggregate statistics about questions grouped by source and subject';
