# Reasoning Level Display Fix

## Problem
The Review page was not showing reasoning effort levels (none/low/medium/high) for rubric and assessment models because the reasoning configs were not being saved to the database.

## Root Cause
- Backend was only saving model NAMES (`rubric_models` and `assessment_models` as TEXT arrays)
- Reasoning configs from `ModelPairSpec` were lost after grading completed
- Frontend had no way to retrieve reasoning information for display

## Solution

### 1. Database Migration ✅
**File:** `app/migrations/002_add_model_pairs_column.sql`

Added `model_pairs` JSONB column to `session` table to store complete model pair specifications:
```sql
ALTER TABLE session ADD COLUMN IF NOT EXISTS model_pairs JSONB;
```

### 2. Backend Changes ✅

**File:** `app/routers/grade.py` (lines 1464-1480)
- Serialize complete model pair data including reasoning configs
- Save to `model_pairs` column as JSON

```python
model_pairs_data = [
    {
        "rubricModel": pair.rubric_model.name,
        "assessmentModel": pair.assessment_model.name,
        "rubricReasoning": pair.rubric_model.reasoning,
        "assessmentReasoning": pair.assessment_model.reasoning,
        "instanceId": pair.instance_id,
    }
    for pair in payload.model_pairs
]
```

**File:** `app/schemas.py` (line 20)
- Added `model_pairs` field to `SessionListItem` schema

**File:** `app/routers/sessions.py` (line 42)
- Return `model_pairs` in session list response

### 3. Frontend Changes ✅

**File:** `src/utils/api.ts` (lines 346-352)
- Updated `SessionListItem` interface to include `model_pairs` with typing

**File:** `src/context/AssessmentContext.tsx` (lines 102-119, 172-189)
- Load `model_pairs` from backend with reasoning configs
- Fallback to legacy array construction for old sessions

**File:** `src/pages/Review.tsx` (lines 35-94)
- Added `getReasoningLabel()` helper
- Added `formatRubricModelLabel()` for rubric models
- Added `formatModelPairLabel()` for model pairs
- Updated all model displays to show reasoning levels

## How to Apply

### Step 1: Run Database Migration
```bash
# In Supabase SQL Editor, run:
app/migrations/002_add_model_pairs_column.sql
```

OR

```bash
# Using Python helper:
python app/migrations/run_migration.py app/migrations/002_add_model_pairs_column.sql
```

### Step 2: Restart Backend
The backend code changes are already applied. Just restart your backend server to load the new code.

### Step 3: Test
1. Create a new assessment with model pairs and reasoning configs
2. Navigate to Review page
3. Verify reasoning levels appear in:
   - Performance Results table (e.g., `gpt-4o — Reasoning: Medium → claude-3.5-sonnet — Reasoning: High`)
   - Question Analysis sections (Both, Rubric Only, Feedback Only tabs)

## Display Format

### Model Pair with Reasoning
```
gpt-4o — Reasoning: Medium → claude-3.5-sonnet — Reasoning: High
```

### Rubric Model Only
```
gpt-4o — Reasoning: Low
```

### Custom Reasoning
```
gpt-4o — Reasoning: Custom (5000 tokens)
```

### No Reasoning
```
gpt-4o
```

## Legacy Support
Old sessions without `model_pairs` will fall back to constructing pairs from `rubric_models` and `assessment_models` arrays (without reasoning info).

## Files Modified
- ✅ `app/migrations/002_add_model_pairs_column.sql`
- ✅ `app/migrations/002_add_model_pairs_column_ROLLBACK.sql`  
- ✅ `app/routers/grade.py`
- ✅ `app/schemas.py`
- ✅ `app/routers/sessions.py`
- ✅ `src/utils/api.ts`
- ✅ `src/context/AssessmentContext.tsx`
- ✅ `src/pages/Review.tsx`
