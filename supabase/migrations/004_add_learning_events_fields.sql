-- Migration 004: Add fields to learning_events for Teacher Command Center
-- Adds event_type and source_text columns for Live Feed and Citation Viewer

-- Add event_type column to distinguish between student and agent actions
ALTER TABLE cortex.learning_events
ADD COLUMN IF NOT EXISTS event_type TEXT
  DEFAULT 'STUDENT_ACTION'
  CHECK (event_type IN ('STUDENT_ACTION', 'AGENT_ACTION'));

-- Add source_text column for citation viewer in student detail modal
ALTER TABLE cortex.learning_events
ADD COLUMN IF NOT EXISTS source_text TEXT;

-- Create indexes for efficient querying of the new columns
CREATE INDEX IF NOT EXISTS idx_learning_events_type
ON cortex.learning_events(event_type);

CREATE INDEX IF NOT EXISTS idx_learning_events_timestamp_type
ON cortex.learning_events(timestamp DESC, event_type);

-- Add comment for documentation
COMMENT ON COLUMN cortex.learning_events.event_type IS 'Type of event: STUDENT_ACTION (user input) or AGENT_ACTION (system response/intervention)';
COMMENT ON COLUMN cortex.learning_events.source_text IS 'Source text/citation for learning events used in student detail modal';
