-- Migration: Verify and Fix Database Schema Issues
-- Version: 1.0
-- Date: 2025-10-21
-- Description: Verifies rubric_result table structure and refreshes schema cache

-- ============================================================================
-- PART 1: Verify rubric_result table structure
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '════════════════════════════════════════════════════════════';
  RAISE NOTICE 'Verifying rubric_result table structure...';
  RAISE NOTICE '════════════════════════════════════════════════════════════';
END $$;

-- Check current columns in rubric_result
SELECT 
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'rubric_result'
ORDER BY ordinal_position;

-- Expected columns (should NOT include any token columns):
-- - id (uuid)
-- - session_id (uuid)
-- - model_name (text)
-- - try_index (integer)
-- - rubric_response (text)
-- - raw_output (jsonb)
-- - validation_errors (jsonb)
-- - created_at (timestamptz)
-- - updated_at (timestamptz)

-- ============================================================================
-- PART 2: Remove any token columns if they exist (cleanup)
-- ============================================================================

-- These columns should NOT exist in rubric_result
-- Token data belongs in token_usage table with phase='rubric'
ALTER TABLE rubric_result 
  DROP COLUMN IF EXISTS cache_creation_input_tokens CASCADE,
  DROP COLUMN IF EXISTS cache_read_input_tokens CASCADE,
  DROP COLUMN IF EXISTS input_tokens CASCADE,
  DROP COLUMN IF EXISTS output_tokens CASCADE,
  DROP COLUMN IF EXISTS reasoning_tokens CASCADE,
  DROP COLUMN IF EXISTS total_tokens CASCADE,
  DROP COLUMN IF EXISTS cost_estimate CASCADE;

DO $$
BEGIN
  RAISE NOTICE '✓ Removed any token columns from rubric_result (if they existed)';
END $$;

-- ============================================================================
-- PART 3: Refresh Supabase schema cache
-- ============================================================================

-- Force Supabase to refresh its schema cache
-- This resolves PGRST204 errors about missing columns
NOTIFY pgrst, 'reload schema';

DO $$
BEGIN
  RAISE NOTICE '✓ Sent schema cache refresh signal to PostgREST';
  RAISE NOTICE '';
  RAISE NOTICE '⚠️  IMPORTANT: You may need to wait 30-60 seconds for the';
  RAISE NOTICE '   schema cache to fully refresh, or restart your Supabase';
  RAISE NOTICE '   connection/client to force an immediate refresh.';
END $$;

-- ============================================================================
-- PART 4: Verify token_usage table has phase column
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '════════════════════════════════════════════════════════════';
  RAISE NOTICE 'Verifying token_usage table structure...';
  RAISE NOTICE '════════════════════════════════════════════════════════════';
  
  IF NOT EXISTS (
    SELECT FROM information_schema.columns 
    WHERE table_schema = 'public' 
      AND table_name = 'token_usage'
      AND column_name = 'phase'
  ) THEN
    RAISE EXCEPTION 'ERROR: phase column does not exist in token_usage table!';
  END IF;
  
  RAISE NOTICE '✓ phase column exists in token_usage';
  RAISE NOTICE '✓ Token tracking is properly configured';
END $$;

-- Check current columns in token_usage
SELECT 
  column_name,
  data_type,
  is_nullable,
  column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'token_usage'
ORDER BY ordinal_position;

-- ============================================================================
-- PART 5: Verify unique constraints
-- ============================================================================

-- Check token_usage unique constraint
SELECT 
  con.conname AS constraint_name,
  array_agg(att.attname ORDER BY att.attnum) AS columns
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(con.conkey)
WHERE nsp.nspname = 'public'
  AND rel.relname = 'token_usage'
  AND con.contype = 'u'
GROUP BY con.conname;

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '════════════════════════════════════════════════════════════';
  RAISE NOTICE '✓ Schema verification and fixes completed!';
  RAISE NOTICE '════════════════════════════════════════════════════════════';
  RAISE NOTICE '';
  RAISE NOTICE 'Summary:';
  RAISE NOTICE '  • rubric_result table: stores rubric extraction results';
  RAISE NOTICE '  • token_usage table: stores ALL token usage with phase column';
  RAISE NOTICE '    - phase=''rubric'': tokens from rubric extraction';
  RAISE NOTICE '    - phase=''assessment'': tokens from grading';
  RAISE NOTICE '';
  RAISE NOTICE 'Next steps:';
  RAISE NOTICE '  1. Review the SELECT query outputs above';
  RAISE NOTICE '  2. Restart your API server if needed';
  RAISE NOTICE '  3. Test grading to verify fixes';
  RAISE NOTICE '════════════════════════════════════════════════════════════';
END $$;
