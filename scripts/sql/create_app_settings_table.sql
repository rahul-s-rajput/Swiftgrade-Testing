-- SQL script to create app_settings table if it doesn't exist
-- Run this in Supabase SQL editor if the table is missing

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create an update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Only create trigger if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_app_settings_updated_at') THEN
        CREATE TRIGGER update_app_settings_updated_at 
        BEFORE UPDATE ON app_settings 
        FOR EACH ROW 
        EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Insert default prompt settings if they don't exist
INSERT INTO app_settings (key, value)
VALUES (
    'prompt_settings',
    '{
        "system_template": "<Role>\nYou are a teacher whose job is to grade student assessments.\n</Role>\n\n<Task>\nYou will be given three inputs:\n- `answer_key`\n- `questions_list`\n- `student_assessments`\nFor each student in `student_assessments`, you must:\n1. Extract the student''s `first_name`, `last_name` and `Student_ID`.\n2. For each question in `questions_list`, assign a `mark` and provide `feedback`.\n3. Format the final output for each student as a single JSON object.\n</Task>\n\n<Instructions>\nFollow the detailed grading instructions and feedback rubric precisely.\n</Instructions>\n\n<Answer_Key>\nHere are the answer key pages. Use these to determine correct answers and any specific grading criteria:\n[Answer key]\n</Answer_Key>\n\n<Question_List>\nHere are the specific questions to grade. Only grade these questions in the student''s assessment:\n[Question list]\n</Question_List>",
        "user_template": "<Student_Assessments>\nHere are the pages of the student''s test:\n[Student assessment]\n</Student_Assessments>"
    }'::jsonb
)
ON CONFLICT (key) DO NOTHING;

-- Verify the table and data
SELECT * FROM app_settings WHERE key = 'prompt_settings';
