-- One-time database cleanup: shrink stored OpenRouter responses.
-- Keeps every assessment, mark, note, rubric and token count; only drops the bulky
-- raw responses (mostly encrypted reasoning) that the app never reads back.
-- Run in the Supabase SQL Editor. Check sizes before/after with:
--   select pg_size_pretty(pg_database_size(current_database()));

-- 1. Per-question result rows: the full response was copied onto every question.
UPDATE result
SET raw_output = NULL
WHERE raw_output IS NOT NULL
  AND question_id NOT IN ('__parse_error__', '__rubric_error__');

-- 2. Parse-error rows and rubric results: keep a slim copy (content, usage, model,
--    provider, finish reason) for debugging.
UPDATE result
SET raw_output = jsonb_strip_nulls(jsonb_build_object(
  'id', raw_output->'id',
  'model', raw_output->'model',
  'provider', raw_output->'provider',
  'usage', raw_output->'usage',
  'error', raw_output->'error',
  'choices', jsonb_build_array(jsonb_build_object(
    'finish_reason', raw_output->'choices'->0->'finish_reason',
    'message', jsonb_build_object('content', raw_output->'choices'->0->'message'->'content')
  ))
))
WHERE question_id = '__parse_error__'
  AND raw_output ? 'choices';

UPDATE rubric_result
SET raw_output = jsonb_strip_nulls(jsonb_build_object(
  'id', raw_output->'id',
  'model', raw_output->'model',
  'provider', raw_output->'provider',
  'usage', raw_output->'usage',
  'error', raw_output->'error',
  'choices', jsonb_build_array(jsonb_build_object(
    'finish_reason', raw_output->'choices'->0->'finish_reason',
    'message', jsonb_build_object('content', raw_output->'choices'->0->'message'->'content')
  ))
))
WHERE raw_output ? 'choices';

-- 3. Give the space back. Postgres only frees it after a full vacuum.
--    Run these two lines as a SEPARATE query afterwards (VACUUM can't run inside
--    the same transaction as the updates above).
-- VACUUM FULL result;
-- VACUUM FULL rubric_result;
