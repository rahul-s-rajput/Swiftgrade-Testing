-- Rollback Migration: Remove Grading Rubric Support
-- Version: 1.0
-- Date: 2025-01-XX
-- Description: Rolls back the grading rubric feature changes

-- ============================================================================
-- WARNING: This will delete all rubric_result data!
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '════════════════════════════════════════════════════════════';
  RAISE NOTICE 'WARNING: Rolling back grading rubric migration';
  RAISE NOTICE 'This will delete all rubric_result data!';
  RAISE NOTICE '════════════════════════════════════════════════════════════';
END $$;

-- ============================================================================
-- PART 1: Drop triggers
-- ============================================================================

DROP TRIGGER IF EXISTS update_rubric_result_updated_at ON rubric_result;

RAISE NOTICE '✓ Triggers dropped';

-- ============================================================================
-- PART 2: Drop indexes
-- ============================================================================

DROP INDEX IF EXISTS idx_rubric_result_session;
DROP INDEX IF EXISTS idx_rubric_result_model_try;
DROP INDEX IF EXISTS idx_rubric_result_session_model;

RAISE NOTICE '✓ Indexes dropped';

-- ============================================================================
-- PART 3: Drop rubric_result table
-- ============================================================================

DROP TABLE IF EXISTS rubric_result CASCADE;

RAISE NOTICE '✓ rubric_result table dropped';

-- ============================================================================
-- PART 4: Restore original image role constraint
-- ============================================================================

-- Drop the updated constraint
ALTER TABLE image DROP CONSTRAINT IF EXISTS image_role_check;

-- Add back the original constraint (without grading_rubric)
ALTER TABLE image ADD CONSTRAINT image_role_check 
  CHECK (role IN ('student', 'answer_key'));

RAISE NOTICE '✓ Image role constraint restored to original';

-- ============================================================================
-- PART 5: Remove session table columns
-- ============================================================================

ALTER TABLE session 
  DROP COLUMN IF EXISTS rubric_models,
  DROP COLUMN IF EXISTS assessment_models;

RAISE NOTICE '✓ Session table restored to original';

-- ============================================================================
-- PART 6: Optionally drop the trigger function if not used elsewhere
-- ============================================================================

-- Uncomment if you want to drop the trigger function
-- (only do this if it's not used by other tables)
-- DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- ============================================================================
-- Rollback complete!
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '════════════════════════════════════════════════════════════';
  RAISE NOTICE '✓ Rollback completed successfully!';
  RAISE NOTICE '✓ All grading rubric changes have been removed';
  RAISE NOTICE '════════════════════════════════════════════════════════════';
END $$;
