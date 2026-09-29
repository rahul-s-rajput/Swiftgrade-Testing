-- Migration 006: usage stats for the in-app storage meter
-- Exposes database size and Storage totals so the app can warn before the
-- Supabase free-plan limits (0.5 GB database, 1 GB storage) are reached.
-- Apply by pasting into the Supabase SQL Editor.

CREATE OR REPLACE FUNCTION public.get_usage_stats()
RETURNS json
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, storage
AS $$
  SELECT json_build_object(
    'db_bytes', pg_database_size(current_database()),
    -- Summed across all buckets: the plan limit applies to the whole project.
    'storage_bytes', COALESCE((SELECT SUM((metadata->>'size')::bigint) FROM storage.objects), 0),
    'storage_objects', (SELECT COUNT(*) FROM storage.objects)
  );
$$;

-- Only the backend (service role) may call it.
REVOKE EXECUTE ON FUNCTION public.get_usage_stats() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_usage_stats() TO service_role;
