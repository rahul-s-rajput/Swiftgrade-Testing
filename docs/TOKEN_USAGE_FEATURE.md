# Token Usage Persistence Feature

This document describes the token usage persistence feature that has been implemented to track and display token usage information for each AI model grading attempt.

## Overview

The token usage persistence feature automatically captures and stores detailed token usage information from OpenRouter API responses, including:
- Input tokens (prompt)
- Output tokens (completion)
- Reasoning tokens (if applicable)
- Total tokens
- Cost estimates
- Cache usage statistics (for models that support caching)

## Features

### 1. **Automatic Token Tracking**
- Token usage is automatically extracted from OpenRouter API responses during grading
- Data is persisted to the `token_usage` table in Supabase
- Each grading attempt's token usage is uniquely tracked by session, model, and attempt number

### 2. **Token Usage Tooltips in UI**
- Hover over the info icon (ℹ️) next to each attempt in the Performance Results tab
- Displays detailed breakdown:
  - Input tokens
  - Output tokens
  - Reasoning tokens (if applicable)
  - Total tokens
  - Estimated cost

### 3. **Cost Estimation**
- Automatic cost calculation based on token usage
- Default pricing (adjustable in code):
  - Input: $3 per 1M tokens
  - Output: $15 per 1M tokens
  - Reasoning: $1 per 1M tokens

### 4. **Token Statistics API**
- Aggregate token usage statistics available via `/stats/{session_id}` endpoint
- Includes per-model totals and per-attempt breakdowns

## Database Schema

The `token_usage` table stores the following information:

```sql
CREATE TABLE token_usage (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    model_name TEXT NOT NULL,
    try_index INTEGER NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (computed),
    cache_creation_input_tokens INTEGER DEFAULT 0,
    cache_read_input_tokens INTEGER DEFAULT 0,
    model_id TEXT,
    finish_reason TEXT,
    cost_estimate DECIMAL(10, 6),
    metadata JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

## Setup Instructions

### 1. Create the Database Table

Run the migration script to create the `token_usage` table in your Supabase database:

#### Option A: Using the Python Script
```bash
python create_token_usage_table.py
```
This will display the SQL that needs to be run in your Supabase SQL editor.

#### Option B: Direct SQL in Supabase
1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Create a new query
4. Copy and paste the SQL from `app/migrations/001_create_token_usage_table.sql`
5. Run the query

### 2. Verify Installation

After creating the table, the feature will automatically start working:
1. Run a new grading assessment
2. Check the Performance Results tab
3. Hover over the info icons to see token usage tooltips

## Implementation Details

### Backend Components

1. **`app/routers/grade.py`**
   - `_extract_token_usage()`: Extracts token data from OpenRouter responses
   - Saves token usage to database after each API call
   - Handles cost estimation

2. **`app/routers/results.py`**
   - Fetches token usage data when retrieving results
   - Maps token data to result items

3. **`app/routers/stats.py`**
   - Aggregates token usage statistics
   - Provides per-model and per-attempt breakdowns

4. **`app/schemas.py`**
   - `TokenUsageItem`: Pydantic model for token usage data
   - Updated `ResultItem` to include optional token_usage field

### Frontend Components

1. **`src/pages/Review.tsx`**
   - Displays token usage tooltips on hover
   - Shows formatted token counts and costs

2. **`src/context/AssessmentContext.tsx`**
   - Maps backend token usage data to frontend types
   - Handles token data in assessment results

3. **`src/types/index.ts`**
   - `tokenUsage` interface for TypeScript typing

## Token Usage Display

The token tooltip shows:
```
Token Usage
─────────────
Input: 1,234
Output: 567
Reasoning: 89
─────────────
Total: 1,890
```

## Troubleshooting

### Token Usage Not Showing

1. **Check if table exists**: Run this SQL in Supabase:
   ```sql
   SELECT * FROM token_usage LIMIT 1;
   ```

2. **Verify data is being saved**: Check backend logs for:
   ```
   📊 Token usage for model_name (try X): input=XXX, output=XXX
   ✅ Saved token usage for X records
   ```

3. **Clear browser cache**: Sometimes cached API responses may not include new fields

### Migration Issues

If the table creation fails:
1. Check foreign key constraints (ensure `session` table exists)
2. Verify PostgreSQL version supports `GENERATED ALWAYS AS` columns
3. Try creating the table without the generated column and add it separately

## API Endpoints

### Get Results with Token Usage
```
GET /results/{session_id}
```
Returns results including token usage per attempt.

### Get Token Statistics
```
GET /stats/{session_id}
```
Returns aggregated token usage statistics.

## Future Enhancements

Potential improvements for the token usage feature:

1. **Historical Analytics Dashboard**
   - Visualize token usage trends over time
   - Compare token efficiency across models

2. **Budget Tracking**
   - Set budget limits per assessment
   - Alerts when approaching budget threshold

3. **Model-Specific Pricing**
   - Accurate pricing for each model based on provider rates
   - Real-time cost updates from OpenRouter pricing API

4. **Export Functionality**
   - Export token usage reports as CSV/PDF
   - Integration with billing systems

## Support

For issues or questions about the token usage persistence feature:
1. Check the backend logs for error messages
2. Verify the database schema is correctly set up
3. Ensure your Supabase connection is properly configured

## License

This feature is part of the Mark Grading Assistant application.