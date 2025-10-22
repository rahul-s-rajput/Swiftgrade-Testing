-- Migration: Add phase column to token_usage table
-- Version: 1.0
-- Date: 2025-01-21
-- Description: Adds phase column to distinguish between rubric and assessment token usage

-- ============================================================================
-- PART 1: Add phase column
-- ============================================================================

-- Add phase column to track whether tokens were used for rubric or assessment
ALTER TABLE token_usage 
  ADD COLUMN IF NOT EXISTS phase TEXT DEFAULT 'assessment' CHECK (phase IN ('rubric', 'assessment'));

-- Add comment
COMMENT ON COLUMN token_usage.phase IS 'Phase of grading: rubric (extraction) or assessment (grading)';

-- ============================================================================
-- PART 2: Update unique constraint to include phase
-- ============================================================================

-- Drop old constraint
ALTER TABLE token_usage DROP CONSTRAINT IF EXISTS unique_token_usage_per_attempt;

-- Add new constraint including phase
ALTER TABLE token_usage 
  ADD CONSTRAINT unique_token_usage_per_attempt 
  UNIQUE (session_id, model_name, try_index, phase);

-- ============================================================================
-- PART 3: Create index for phase queries
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_token_usage_phase 
  ON token_usage(phase);

-- ============================================================================
-- PART 4: Verify migration
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT FROM information_schema.columns 
    WHERE table_schema = 'public' 
    AND table_name = 'token_usage'
    AND column_name = 'phase'
  ) THEN
    RAISE EXCEPTION 'Migration failed: phase column not added to token_usage';
  END IF;
  
  RAISE NOTICE '✓ phase column added to token_usage successfully';
  RAISE NOTICE '✓ Unique constraint updated to include phase';
  RAISE NOTICE '✓ Index created for phase queries';
  RAISE NOTICE '════════════════════════════════════════════════════════════';
  RAISE NOTICE '✓ Migration completed successfully!';
  RAISE NOTICE '════════════════════════════════════════════════════════════';
END $$;
