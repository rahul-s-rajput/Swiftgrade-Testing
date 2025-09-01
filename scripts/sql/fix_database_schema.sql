-- Fix database schema for Essay Grading Backend
-- Run this in Supabase SQL Editor

-- Drop existing tables if needed (BE CAREFUL - this will delete all data)
-- Uncomment these lines if you want to start fresh:
-- DROP TABLE IF EXISTS stats CASCADE;
-- DROP TABLE IF EXISTS result CASCADE;
-- DROP TABLE IF EXISTS question CASCADE;
-- DROP TABLE IF EXISTS image CASCADE;
-- DROP TABLE IF EXISTS session CASCADE;

-- Create session table
CREATE TABLE IF NOT EXISTS session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'grading', 'graded', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create image table (using 'role' not 'kind')
CREATE TABLE IF NOT EXISTS image (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES session(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('student', 'answer_key')),
    url TEXT NOT NULL,
    order_index INTEGER NOT NULL CHECK (order_index >= 0),
    storage_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_image_session_url UNIQUE(session_id, url),
    CONSTRAINT uq_image_session_role_order UNIQUE(session_id, role, order_index)
);
CREATE INDEX IF NOT EXISTS idx_image_session ON image(session_id);

-- Create question table
CREATE TABLE IF NOT EXISTS question (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES session(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL,
    number INTEGER NOT NULL CHECK (number > 0),
    max_marks NUMERIC NOT NULL CHECK (max_marks >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_question_session_qid UNIQUE(session_id, question_id)
);
CREATE INDEX IF NOT EXISTS idx_question_session ON question(session_id);

-- Create result table (properly structured)
CREATE TABLE IF NOT EXISTS result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES session(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    try_index INTEGER NOT NULL CHECK (try_index > 0),
    marks_awarded NUMERIC,
    rubric_notes TEXT,
    raw_output JSONB,
    raw_output_url TEXT,
    validation_errors JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_result_session_q_model_try UNIQUE(session_id, question_id, model_name, try_index)
);
CREATE INDEX IF NOT EXISTS idx_result_session_q ON result(session_id, question_id);
CREATE INDEX IF NOT EXISTS idx_result_model_try ON result(session_id, model_name, try_index);

-- Create stats table (with correct columns for new implementation)
CREATE TABLE IF NOT EXISTS stats (
    session_id UUID PRIMARY KEY REFERENCES session(id) ON DELETE CASCADE,
    human_marks_by_qid JSONB NOT NULL DEFAULT '{}'::JSONB,
    totals JSONB NOT NULL DEFAULT '{}'::JSONB,
    discrepancies_by_model_try JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add update trigger for session.updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_session_updated_at BEFORE UPDATE ON session
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stats_updated_at BEFORE UPDATE ON stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant necessary permissions (adjust as needed)
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;
