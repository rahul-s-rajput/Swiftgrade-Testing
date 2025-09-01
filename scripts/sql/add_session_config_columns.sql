-- Migration: add persisted session configuration fields
-- Run this in Supabase SQL Editor

ALTER TABLE IF EXISTS session
  ADD COLUMN IF NOT EXISTS default_tries INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS selected_models TEXT[] NOT NULL DEFAULT '{}';

-- Backfill is optional; leaving defaults for historical sessions.

-- Ensure privileges (optional; assuming service_role already has full perms)
