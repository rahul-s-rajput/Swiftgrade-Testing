-- Create app_settings key-value table for storing prompt templates
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Optional: basic RLS or grants depending on your setup
-- GRANT ALL ON TABLE app_settings TO service_role;
