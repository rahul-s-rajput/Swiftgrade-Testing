-- Migration: Add Grading Rubric Support
-- Version: 1.0
-- Date: 2025-01-XX
-- Description: Adds support for grading rubric feature with model pairs

-- ============================================================================
-- PART 1: Create rubric_result table
-- ============================================================================

CREATE TABLE IF NOT EXISTS rubric_result (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id UUID NOT NULL,
  model_name TEXT NOT NULL,
  try_index INTEGER NOT NULL,
  rubric_response TEXT,
  raw_output JSONB,
  validation_errors JSONB,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  
  -- Foreign key constraint
  CONSTRAINT fk_rubric_result_session 
    FOREIGN KEY (session_id) 
    REFERENCES session(id) 
    ON DELETE CASCADE,
  
  -- Unique constraint to prevent duplicate entries
  CONSTRAINT unique_rubric_per_attempt 
    UNIQUE (session_id, model_name, try_index)
);

-- Add comment to table
COMMENT ON TABLE rubric_result IS 'Stores results from grading rubric analysis LLM calls';
COMMENT ON COLUMN rubric_result.session_id IS 'Reference to the assessment session';
COMMENT ON COLUMN rubric_result.model_name IS 'Identifier for the rubric model used (may include instance_id)';
COMMENT ON COLUMN rubric_result.try_index IS 'Attempt number for this model';
COMMENT ON COLUMN rubric_result.rubric_response IS 'Extracted rubric text from the LLM response';
COMMENT ON COLUMN rubric_result.raw_output IS 'Full JSON response from OpenRouter API';
COMMENT ON COLUMN rubric_result.validation_errors IS 'Errors encountered during parsing/validation';

-- ============================================================================
-- PART 2: Create indexes for rubric_result
-- ============================================================================

-- Index for querying by session
CREATE INDEX IF NOT EXISTS idx_rubric_result_session 
  ON rubric_result(session_id);

-- Index for querying by model and try
CREATE INDEX IF NOT EXISTS idx_rubric_result_model_try 
  ON rubric_result(model_name, try_index);

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_rubric_result_session_model 
  ON rubric_result(session_id, model_name, try_index);

-- ============================================================================
-- PART 3: Update image table to support grading_rubric role
-- ============================================================================

-- Drop existing constraint if it exists
ALTER TABLE image DROP CONSTRAINT IF EXISTS image_role_check;

-- Add new constraint with grading_rubric role
ALTER TABLE image ADD CONSTRAINT image_role_check 
  CHECK (role IN ('student', 'answer_key', 'grading_rubric'));

-- Add comment
COMMENT ON CONSTRAINT image_role_check ON image IS 'Validates image role: student, answer_key, or grading_rubric';

-- ============================================================================
-- PART 4: Update session table to track model pairs
-- ============================================================================

-- Add columns for model pair tracking (optional metadata)
ALTER TABLE session 
  ADD COLUMN IF NOT EXISTS rubric_models TEXT[],
  ADD COLUMN IF NOT EXISTS assessment_models TEXT[];

-- Add comments
COMMENT ON COLUMN session.rubric_models IS 'Array of rubric model IDs used in this session';
COMMENT ON COLUMN session.assessment_models IS 'Array of assessment model IDs used in this session';

-- ============================================================================
-- PART 5: Add trigger for updated_at on rubric_result
-- ============================================================================

-- Create or replace the trigger function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to rubric_result table
DROP TRIGGER IF EXISTS update_rubric_result_updated_at ON rubric_result;
CREATE TRIGGER update_rubric_result_updated_at
  BEFORE UPDATE ON rubric_result
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PART 6: Verify migration
-- ============================================================================

-- Check that rubric_result table was created
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT FROM pg_tables 
    WHERE schemaname = 'public' 
    AND tablename = 'rubric_result'
  ) THEN
    RAISE EXCEPTION 'Migration failed: rubric_result table not created';
  END IF;
  
  RAISE NOTICE '✓ rubric_result table created successfully';
END $$;

-- Check that indexes were created
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename = 'rubric_result'
    AND indexname = 'idx_rubric_result_session'
  ) THEN
    RAISE EXCEPTION 'Migration failed: idx_rubric_result_session not created';
  END IF;
  
  RAISE NOTICE '✓ Indexes created successfully';
END $$;

-- Check that image constraint was updated
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT FROM pg_constraint 
    WHERE conname = 'image_role_check'
  ) THEN
    RAISE EXCEPTION 'Migration failed: image_role_check constraint not created';
  END IF;
  
  RAISE NOTICE '✓ Image role constraint updated successfully';
END $$;

-- Check that session columns were added
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT FROM information_schema.columns 
    WHERE table_schema = 'public' 
    AND table_name = 'session'
    AND column_name = 'rubric_models'
  ) THEN
    RAISE EXCEPTION 'Migration failed: rubric_models column not added to session';
  END IF;
  
  RAISE NOTICE '✓ Session table updated successfully';
END $$;

-- ============================================================================
-- PART 7: Grant permissions (adjust as needed for your setup)
-- ============================================================================

-- Grant permissions to authenticated role (Supabase default)
-- Uncomment and adjust if needed:
-- GRANT SELECT, INSERT, UPDATE, DELETE ON rubric_result TO authenticated;
-- GRANT USAGE, SELECT ON SEQUENCE rubric_result_id_seq TO authenticated;

-- ============================================================================
-- Migration complete!
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '════════════════════════════════════════════════════════════';
  RAISE NOTICE '✓ Migration completed successfully!';
  RAISE NOTICE '✓ rubric_result table created';
  RAISE NOTICE '✓ Indexes created for performance';
  RAISE NOTICE '✓ Image role constraint updated';
  RAISE NOTICE '✓ Session table updated with model pair tracking';
  RAISE NOTICE '✓ Triggers added for updated_at';
  RAISE NOTICE '════════════════════════════════════════════════════════════';
END $$;
