# Backend Fix Instructions

## Problem Summary
The backend is failing due to:
1. **Missing `result` table** - The grading code tries to save results to a `result` table that doesn't exist
2. **Missing database URL** - The SQLAlchemy connection needs SUPABASE_DB_URL environment variable

## Solution

### Step 1: Create the Missing Result Table
Run this SQL in your Supabase SQL Editor:

```sql
-- Create the missing result table for storing grading results
CREATE TABLE public.result (
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
  CONSTRAINT result_try_index_check CHECK ((try_index >= 1))
) TABLESPACE pg_default;

-- Create indexes for better query performance
CREATE INDEX idx_result_session_id ON public.result (session_id);
CREATE INDEX idx_result_model_name ON public.result (model_name);
CREATE INDEX idx_result_question_id ON public.result (question_id);
CREATE INDEX idx_result_created_at ON public.result (created_at);
```

### Step 2: Add Database URL to .env
Get your database URL from Supabase:
1. Go to your Supabase project dashboard
2. Click on Settings → Database
3. Copy the "Connection string" (URI)
4. Add it to your .env file:

```env
# Add this line to your .env file
SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.bfyrqdjuqipaummsxkbi.supabase.co:5432/postgres
```

Replace [YOUR-PASSWORD] with your actual database password.

### Step 3: Fix the Results Router
The results router is also trying to read from the `result` table. This is already implemented correctly, we just need the table to exist.

## Alternative Solution (If you don't want to add a result table)
If you prefer to store results in the existing `stats` table as JSONB, we would need to modify:
- `grade.py` to store results in the stats table
- `results.py` to read from the stats table
- `stats.py` to read from the stats table

Let me know which approach you prefer!

## Quick Test
After making these changes:
1. Restart your FastAPI server
2. Try creating a new assessment
3. Check the browser console for any remaining errors
