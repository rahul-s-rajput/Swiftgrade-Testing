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
