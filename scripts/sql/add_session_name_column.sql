-- Migration: add name column to session table
-- Safe to run multiple times
ALTER TABLE IF EXISTS public.session
  ADD COLUMN IF NOT EXISTS name text;
