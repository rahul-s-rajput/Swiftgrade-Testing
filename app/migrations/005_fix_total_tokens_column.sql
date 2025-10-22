-- Fix total_tokens column to use OpenRouter's actual total_tokens value instead of calculated value

-- First, drop the generated column constraint
ALTER TABLE token_usage DROP COLUMN IF EXISTS total_tokens;

-- Add total_tokens as a regular integer column that will store OpenRouter's actual total_tokens value
ALTER TABLE token_usage ADD COLUMN total_tokens integer null DEFAULT 0;

-- Add comment to clarify this should store OpenRouter's total_tokens value
COMMENT ON COLUMN token_usage.total_tokens IS 'Total tokens from OpenRouter response (should use usage.total_tokens directly, not calculated)';

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_token_usage_total_tokens ON public.token_usage(total_tokens) TABLESPACE pg_default;