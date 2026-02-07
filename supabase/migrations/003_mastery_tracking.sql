-- ============================================================================
-- Migration 003: Mastery Tracking with Bayesian Knowledge Tracing
-- Implements Learning Record Store (LRS) for student mastery tracking
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Create Skills Registry (defines available skills to track)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cortex.skills_registry (
    skill_id TEXT PRIMARY KEY,
    skill_name TEXT NOT NULL,
    subject TEXT DEFAULT 'science',
    grade_level INTEGER DEFAULT 8,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 2. Create Learning Events Table (granular interactions)
-- Each student interaction is recorded here
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cortex.learning_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    skill_id TEXT NOT NULL REFERENCES cortex.skills_registry(skill_id) ON DELETE CASCADE,
    is_correct BOOLEAN NOT NULL,
    attempts INTEGER DEFAULT 1,
    time_spent_seconds INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 3. Create Student Skills Table (mastery probabilities)
-- Stores current mastery state for each student-skill pair
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cortex.student_skills (
    user_id UUID NOT NULL,
    skill_id TEXT NOT NULL REFERENCES cortex.skills_registry(skill_id) ON DELETE CASCADE,
    probability_mastery FLOAT DEFAULT 0.5 CHECK (probability_mastery >= 0 AND probability_mastery <= 1),
    total_attempts INTEGER DEFAULT 0,
    correct_attempts INTEGER DEFAULT 0,
    consecutive_correct INTEGER DEFAULT 0,
    consecutive_incorrect INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, skill_id)
);

-- ----------------------------------------------------------------------------
-- 4. Indexes for performance
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_learning_events_user_skill ON cortex.learning_events(user_id, skill_id);
CREATE INDEX IF NOT EXISTS idx_learning_events_timestamp ON cortex.learning_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_learning_events_user ON cortex.learning_events(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_events_skill ON cortex.learning_events(skill_id);
CREATE INDEX IF NOT EXISTS idx_student_skills_user ON cortex.student_skills(user_id);
CREATE INDEX IF NOT EXISTS idx_student_skills_mastery ON cortex.student_skills(probability_mastery);
CREATE INDEX IF NOT EXISTS idx_student_skills_skill ON cortex.student_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_skills_registry_subject ON cortex.skills_registry(subject, grade_level);

-- ----------------------------------------------------------------------------
-- 5. Enable Row Level Security
-- ----------------------------------------------------------------------------
ALTER TABLE cortex.skills_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE cortex.learning_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE cortex.student_skills ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- 6. RLS Policies
-- ----------------------------------------------------------------------------

-- Skills Registry: Everyone can read, only instructors/admins can write
CREATE POLICY "Everyone can view skills registry"
ON cortex.skills_registry FOR SELECT
TO authenticated, anon
USING (true);

CREATE POLICY "Instructors can manage skills registry"
ON cortex.skills_registry FOR ALL
TO authenticated
USING (auth.jwt() ->> 'role' IN ('instructor', 'admin'))
WITH CHECK (auth.jwt() ->> 'role' IN ('instructor', 'admin'));

-- Learning Events: Instructors can view all, students can view own
CREATE POLICY "Instructors can view all learning events"
ON cortex.learning_events FOR SELECT
TO authenticated
USING (auth.jwt() ->> 'role' IN ('instructor', 'admin'));

CREATE POLICY "Students can view own events"
ON cortex.learning_events FOR SELECT
TO authenticated
USING (auth.jwt() ->> 'user_id'::text = user_id::text);

CREATE POLICY "System can insert learning events"
ON cortex.learning_events FOR INSERT
TO authenticated
WITH CHECK (auth.jwt() ->> 'role' IN ('instructor', 'admin', 'system'));

-- Student Skills: Instructors can view all, students can view own
CREATE POLICY "Instructors can view all student skills"
ON cortex.student_skills FOR SELECT
TO authenticated
USING (auth.jwt() ->> 'role' IN ('instructor', 'admin'));

CREATE POLICY "Students can view own skills"
ON cortex.student_skills FOR SELECT
TO authenticated
USING (auth.jwt() ->> 'user_id'::text = user_id::text);

CREATE POLICY "System can update student skills"
ON cortex.student_skills FOR ALL
TO authenticated
USING (auth.jwt() ->> 'role' IN ('instructor', 'admin', 'system'))
WITH CHECK (auth.jwt() ->> 'role' IN ('instructor', 'admin', 'system'));

-- ----------------------------------------------------------------------------
-- 7. Trigger function to update student_skills on new learning_event
-- Implements basic BKT-style update (will be enhanced by Python service)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cortex.update_mastery_on_event()
RETURNS TRIGGER AS $$
DECLARE
    current_prob FLOAT;
    new_prob FLOAT;
    current_correct INTEGER;
    current_total INTEGER;
    current_consec_correct INTEGER;
    current_consec_incorrect INTEGER;
BEGIN
    -- Get current state or initialize
    SELECT probability_mastery, correct_attempts, total_attempts, consecutive_correct, consecutive_incorrect
    INTO current_prob, current_correct, current_total, current_consec_correct, current_consec_incorrect
    FROM cortex.student_skills
    WHERE user_id = NEW.user_id AND skill_id = NEW.skill_id
    FOR UPDATE;

    -- Simple BKT-style update (Python service will use full pyBKT)
    IF NEW.is_correct THEN
        new_prob := LEAST(1.0, COALESCE(current_prob, 0.5) + 0.1);
    ELSE
        new_prob := GREATEST(0.0, COALESCE(current_prob, 0.5) - 0.05);
    END IF;

    -- Update consecutive counters
    IF NEW.is_correct THEN
        current_consec_correct := COALESCE(current_consec_correct, 0) + 1;
        current_consec_incorrect := 0;
    ELSE
        current_consec_incorrect := COALESCE(current_consec_incorrect, 0) + 1;
        current_consec_correct := 0;
    END IF;

    -- Insert or update student_skills
    INSERT INTO cortex.student_skills (
        user_id, skill_id, probability_mastery,
        total_attempts, correct_attempts,
        consecutive_correct, consecutive_incorrect,
        last_attempt_at, last_updated_at
    )
    VALUES (
        NEW.user_id, NEW.skill_id, new_prob,
        COALESCE(current_total, 0) + NEW.attempts,
        COALESCE(current_correct, 0) + CASE WHEN NEW.is_correct THEN 1 ELSE 0 END,
        current_consec_correct,
        current_consec_incorrect,
        NEW.timestamp, NOW()
    )
    ON CONFLICT (user_id, skill_id) DO UPDATE SET
        probability_mastery = EXCLUDED.probability_mastery,
        total_attempts = EXCLUDED.total_attempts,
        correct_attempts = EXCLUDED.correct_attempts,
        consecutive_correct = EXCLUDED.consecutive_correct,
        consecutive_incorrect = EXCLUDED.consecutive_incorrect,
        last_attempt_at = EXCLUDED.last_attempt_at,
        last_updated_at = EXCLUDED.last_updated_at;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trigger_update_mastery ON cortex.learning_events;
CREATE TRIGGER trigger_update_mastery
    AFTER INSERT ON cortex.learning_events
    FOR EACH ROW
    EXECUTE FUNCTION cortex.update_mastery_on_event();

-- ----------------------------------------------------------------------------
-- 8. Helper Functions
-- ----------------------------------------------------------------------------

-- Function to get student mastery status with classification
CREATE OR REPLACE FUNCTION cortex.get_student_mastery_status(p_user_id UUID)
RETURNS TABLE (
    skill_id TEXT,
    skill_name TEXT,
    probability_mastery FLOAT,
    total_attempts INTEGER,
    correct_attempts INTEGER,
    status TEXT,
    suggested_action TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ss.skill_id,
        sr.skill_name,
        ss.probability_mastery,
        ss.total_attempts,
        ss.correct_attempts,
        CASE
            WHEN ss.probability_mastery < 0.6 AND ss.total_attempts > 3 THEN 'STRUGGLING'
            WHEN ss.probability_mastery > 0.9 THEN 'MASTERED'
            ELSE 'LEARNING'
        END as status,
        CASE
            WHEN ss.probability_mastery < 0.6 AND ss.total_attempts > 3 THEN 'Provide remediation and scaffolding'
            WHEN ss.probability_mastery > 0.9 THEN 'Ready for next challenge'
            ELSE 'Continue practice'
        END as suggested_action
    FROM cortex.student_skills ss
    JOIN cortex.skills_registry sr ON ss.skill_id = sr.skill_id
    WHERE ss.user_id = p_user_id
    ORDER BY ss.last_attempt_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION cortex.get_student_mastery_status TO authenticated;

-- Function to get class overview (for teacher dashboard)
CREATE OR REPLACE FUNCTION cortex.get_class_mastery_overview()
RETURNS TABLE (
    user_id UUID,
    total_skills INTEGER,
    mastered_count INTEGER,
    learning_count INTEGER,
    struggling_count INTEGER,
    avg_mastery FLOAT,
    last_active TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ss.user_id,
        COUNT(*) as total_skills,
        COUNT(*) FILTER (WHERE ss.probability_mastery > 0.9) as mastered_count,
        COUNT(*) FILTER (WHERE ss.probability_mastery >= 0.6 AND ss.probability_mastery <= 0.9) as learning_count,
        COUNT(*) FILTER (WHERE ss.probability_mastery < 0.6 AND ss.total_attempts > 3) as struggling_count,
        AVG(ss.probability_mastery) as avg_mastery,
        MAX(ss.last_attempt_at) as last_active
    FROM cortex.student_skills ss
    GROUP BY ss.user_id
    ORDER BY last_active DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION cortex.get_class_mastery_overview TO authenticated;

-- Function to record a learning event (simplified API)
CREATE OR REPLACE FUNCTION cortex.record_learning(
    p_user_id UUID,
    p_skill_id TEXT,
    p_is_correct BOOLEAN,
    p_attempts INTEGER DEFAULT 1,
    p_time_spent_seconds INTEGER DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
    event_id UUID;
BEGIN
    -- Insert the learning event (trigger will update student_skills)
    INSERT INTO cortex.learning_events (
        user_id, skill_id, is_correct, attempts,
        time_spent_seconds, metadata
    )
    VALUES (
        p_user_id, p_skill_id, p_is_correct, p_attempts,
        p_time_spent_seconds, p_metadata
    )
    RETURNING cortex.learning_events.id INTO event_id;

    RETURN event_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION cortex.record_learning TO authenticated;

-- ----------------------------------------------------------------------------
-- 9. Views for common queries
-- ----------------------------------------------------------------------------

-- View for struggling students (teacher dashboard alert)
CREATE OR REPLACE VIEW cortex.struggling_students AS
SELECT
    ss.user_id,
    ss.skill_id,
    sr.skill_name,
    ss.probability_mastery,
    ss.total_attempts,
    ss.consecutive_incorrect,
    ss.last_attempt_at,
    sr.subject,
    sr.grade_level
FROM cortex.student_skills ss
JOIN cortex.skills_registry sr ON ss.skill_id = sr.skill_id
WHERE ss.probability_mastery < 0.6
  AND ss.total_attempts > 3
  AND ss.consecutive_incorrect >= 2
ORDER BY ss.last_attempt_at DESC;

-- View for mastery progress by skill
CREATE OR REPLACE VIEW cortex.skill_mastery_summary AS
SELECT
    sr.skill_id,
    sr.skill_name,
    sr.subject,
    sr.grade_level,
    COUNT(DISTINCT ss.user_id) as total_students,
    COUNT(DISTINCT ss.user_id) FILTER (WHERE ss.probability_mastery > 0.9) as mastered_count,
    COUNT(DISTINCT ss.user_id) FILTER (WHERE ss.probability_mastery < 0.6 AND ss.total_attempts > 3) as struggling_count,
    AVG(ss.probability_mastery) as avg_mastery,
    AVG(ss.total_attempts) as avg_attempts
FROM cortex.skills_registry sr
LEFT JOIN cortex.student_skills ss ON sr.skill_id = ss.skill_id
GROUP BY sr.skill_id, sr.skill_name, sr.subject, sr.grade_level
ORDER BY sr.skill_id;

-- ----------------------------------------------------------------------------
-- 10. Comments for documentation
-- ----------------------------------------------------------------------------
COMMENT ON TABLE cortex.skills_registry IS 'Registry of skills available for mastery tracking';
COMMENT ON TABLE cortex.learning_events IS 'Granular log of all student learning interactions';
COMMENT ON TABLE cortex.student_skills IS 'Current mastery state for each student-skill pair using Bayesian Knowledge Tracing';
COMMENT ON FUNCTION cortex.update_mastery_on_event IS 'Trigger function that updates student_skills when new learning_events are inserted';
COMMENT ON FUNCTION cortex.get_student_mastery_status IS 'Returns classified mastery status (MASTERED/LEARNING/STRUGGLING) for a student';
COMMENT ON FUNCTION cortex.get_class_mastery_overview IS 'Aggregated class view for teacher dashboard';
COMMENT ON FUNCTION cortex.record_learning IS 'Simplified API to record learning events and trigger BKT update';
COMMENT ON VIEW cortex.struggling_students IS 'Students who need intervention (low mastery + multiple attempts)';
COMMENT ON VIEW cortex.skill_mastery_summary IS 'Aggregate mastery statistics by skill';
