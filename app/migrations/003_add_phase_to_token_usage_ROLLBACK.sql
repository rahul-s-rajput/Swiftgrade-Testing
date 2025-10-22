-- Rollback Migration: Remove phase column from token_usage table
-- Version: 1.0
-- Date: 2025-01-21

-- ============================================================================
-- PART 1: Restore original unique constraint
-- ============================================================================

-- Drop new constraint
ALTER TABLE token_usage DROP CONSTRAINT IF EXISTS unique_token_usage_per_attempt;

-- Restore original constraint (without phase)
ALTER TABLE token_usage 
  ADD CONSTRAINT unique_token_usage_per_attempt 
  UNIQUE (session_id, model_name, try_index);

-- ============================================================================
-- PART 2: Remove phase column
-- ============================================================================

ALTER TABLE token_usage DROP COLUMN IF EXISTS phase;

-- ============================================================================
-- PART 3: Drop phase index
-- ============================================================================

DROP INDEX IF EXISTS idx_token_usage_phase;

-- ============================================================================
-- Rollback complete
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '✓ Rollback completed successfully';
  RAISE NOTICE '✓ phase column removed from token_usage';
  RAISE NOTICE '✓ Original unique constraint restored';
END $$;
