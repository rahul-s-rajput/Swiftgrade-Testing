# BACKEND FIX - COMPLETE SOLUTION

## Issue Summary
Your backend is failing because:
1. **Missing `result` table** - The grading system needs this table to store results
2. **Database URL not needed** - Since you're using Supabase client directly, not SQLAlchemy

## SOLUTION - Create the Missing Table

### Step 1: Create the Result Table in Supabase

Go to your Supabase project SQL editor and run this SQL:

```sql
-- Create the result table for storing grading results
CREATE TABLE IF NOT EXISTS public.result (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL,
  question_id text NOT NULL,
  model_name text NOT NULL,
  try_index integer NOT NULL DEFAULT 1,
  marks_awarded numeric(10, 2),
  rubric_notes text,
  raw_output jsonb,
  validation_errors jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT result_pkey PRIMARY KEY (id),
  CONSTRAINT result_session_id_question_id_model_name_try_index_key UNIQUE (session_id, question_id, model_name, try_index),
  CONSTRAINT result_session_id_fkey FOREIGN KEY (session_id) REFERENCES session (id) ON DELETE CASCADE,
  CONSTRAINT result_try_index_check CHECK (try_index >= 1)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_result_session_id ON public.result (session_id);
CREATE INDEX IF NOT EXISTS idx_result_model_name ON public.result (model_name);
CREATE INDEX IF NOT EXISTS idx_result_question_id ON public.result (question_id);
CREATE INDEX IF NOT EXISTS idx_result_created_at ON public.result (created_at);
```

### Step 2: Verify Your Tables

After running the SQL above, verify you have all 5 tables in Supabase:
1. `session` ✓ (you have this)
2. `image` ✓ (you have this)
3. `question` ✓ (you have this)
4. `stats` ✓ (you have this)
5. `result` ← NEW TABLE (just created)

### Step 3: Restart Your Backend

```bash
# Stop the current server (Ctrl+C)
# Then restart it:
uvicorn app.main:app --reload --port 8000
```

## That's It!

The backend should now work correctly. The error messages were happening because:
- `/questions/config` was failing when trying to save stats
- `/grade/single` was failing when trying to save results to the non-existent `result` table
- The stats calculations were expecting the `result` table to exist

## Test Your Fix

1. Open your frontend (http://localhost:5173)
2. Try creating a new assessment
3. Upload images
4. Configure questions
5. Start grading

The errors should be gone!

## Note
- You DON'T need to add SUPABASE_DB_URL to your .env file
- Your code is already using the Supabase client directly (not SQLAlchemy)
- The db.py file exists but isn't being used
