-- ============================================================================
-- Rollback: Remove model_pairs column from session table
-- ============================================================================

-- Drop index
DROP INDEX IF EXISTS idx_session_model_pairs;

-- Drop column
ALTER TABLE session 
  DROP COLUMN IF EXISTS model_pairs;

RAISE NOTICE '✓ model_pairs column removed successfully';
