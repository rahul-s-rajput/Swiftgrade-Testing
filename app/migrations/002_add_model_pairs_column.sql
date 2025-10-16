-- ============================================================================
-- Migration: Add model_pairs JSONB column to session table
-- Description: Stores complete model pair specifications including reasoning configs
-- ============================================================================

-- Add model_pairs JSONB column
ALTER TABLE session 
  ADD COLUMN IF NOT EXISTS model_pairs JSONB;

-- Add comment
COMMENT ON COLUMN session.model_pairs IS 'Complete model pair specifications including reasoning configs (JSONB array)';

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_session_model_pairs 
  ON session USING GIN (model_pairs);

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT FROM information_schema.columns 
    WHERE table_schema = 'public' 
    AND table_name = 'session'
    AND column_name = 'model_pairs'
  ) THEN
    RAISE EXCEPTION 'Migration failed: model_pairs column not created';
  END IF;
  
  RAISE NOTICE '✓ model_pairs column added successfully';
END $$;
