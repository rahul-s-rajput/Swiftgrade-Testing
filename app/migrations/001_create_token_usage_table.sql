-- Create token_usage table to persist token usage data for each grading attempt
CREATE TABLE IF NOT EXISTS token_usage (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL,
    model_name TEXT NOT NULL,
    try_index INTEGER NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens + COALESCE(reasoning_tokens, 0)) STORED,
    cache_creation_input_tokens INTEGER DEFAULT 0,
    cache_read_input_tokens INTEGER DEFAULT 0,
    model_id TEXT,
    finish_reason TEXT,
    cost_estimate DECIMAL(10, 6),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key to session table
    CONSTRAINT fk_session 
        FOREIGN KEY (session_id) 
        REFERENCES session(id) 
        ON DELETE CASCADE,
    
    -- Unique constraint to prevent duplicates
    CONSTRAINT unique_token_usage_per_attempt 
        UNIQUE (session_id, model_name, try_index)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_token_usage_session_id ON token_usage(session_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_model_name ON token_usage(model_name);
CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON token_usage(created_at);

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_token_usage_updated_at 
    BEFORE UPDATE ON token_usage 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add comment to table
COMMENT ON TABLE token_usage IS 'Stores token usage information for each AI model grading attempt';
COMMENT ON COLUMN token_usage.session_id IS 'Reference to the grading session';
COMMENT ON COLUMN token_usage.model_name IS 'Name of the AI model used (e.g., claude-3-opus)';
COMMENT ON COLUMN token_usage.try_index IS 'Attempt number for this model in this session';
COMMENT ON COLUMN token_usage.input_tokens IS 'Number of tokens in the input/prompt';
COMMENT ON COLUMN token_usage.output_tokens IS 'Number of tokens in the output/completion';
COMMENT ON COLUMN token_usage.reasoning_tokens IS 'Number of tokens used for reasoning (if applicable)';
COMMENT ON COLUMN token_usage.total_tokens IS 'Total tokens used (auto-calculated)';
COMMENT ON COLUMN token_usage.cache_creation_input_tokens IS 'Tokens used for cache creation (Claude specific)';
COMMENT ON COLUMN token_usage.cache_read_input_tokens IS 'Tokens read from cache (Claude specific)';
COMMENT ON COLUMN token_usage.cost_estimate IS 'Estimated cost in USD for this request';
COMMENT ON COLUMN token_usage.metadata IS 'Additional metadata from the API response';
