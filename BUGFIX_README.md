# Bug Fixes - October 21, 2025

## Summary of Issues Fixed

This update addresses 3 critical bugs identified in the grading system:

1. **Database Schema Error** - Missing `cache_creation_input_tokens` column in `rubric_result` table
2. **JSON Parse Errors** - Invalid escape sequences from Gemini models causing parse failures
3. **Token Storage Architecture** - Rubric and assessment tokens now properly tracked in `token_usage` table

---

## 🔧 Changes Made

### 1. **Database Migration** - Add Phase Column to `token_usage`

**Files Created:**
- `app/migrations/003_add_phase_to_token_usage.sql` - Migration
- `app/migrations/003_add_phase_to_token_usage_ROLLBACK.sql` - Rollback
- `app/migrations/run_phase_migration.py` - Migration runner script

**What it does:**
- Adds `phase` column to `token_usage` table (values: 'rubric' or 'assessment')
- Updates unique constraint to include `phase`
- Creates index for efficient phase queries
- **IMPORTANT:** This allows both rubric and assessment token usage to be stored in the same table for each attempt

**Benefits:**
- Single source of truth for all token usage
- Easy to query and analyze in Performance Analysis tab
- Proper separation between rubric extraction costs and assessment costs

### 2. **JSON Parser Utility** - Handle Invalid Escape Sequences

**Files Created:**
- `app/util/json_parser.py` - New utility module

**What it does:**
- Sanitizes invalid escape sequences (\\t, \\n, \\r, etc.) from LLM responses
- Extracts JSON from markdown code blocks
- Handles preamble text before JSON
- Uses brace matching for robust extraction
- Falls back gracefully with detailed error messages

**Benefits:**
- Fixes Gemini model JSON parse errors
- More robust handling of all LLM response formats
- Better error diagnostics for debugging

### 3. **Updated Grading Logic** - Use New Parser & Token Storage

**Files Modified:**
- `app/routers/grade.py`

**Changes:**
1. Import new JSON parser utilities
2. Updated `_call_rubric_llm()`:
   - Uses new JSON parser for rubric extraction
   - Stores rubric tokens in `token_usage` table with `phase='rubric'`
   - Removed token columns from `rubric_result` upsert
3. Updated `_parse_model_output()`:
   - Uses new JSON parser for assessment responses
   - Automatically sanitizes invalid escape sequences
4. Updated token storage:
   - Assessment tokens use `phase='assessment'`
   - Legacy flow tokens use `phase='assessment'`
   - Updated upsert conflict clause to include `phase`

---

## 📝 How to Apply These Fixes

### Step 1: Run the Database Migration

**Option A: Using Python Script (Recommended)**

```bash
# Navigate to project directory
cd C:\Users\rajpu\Downloads\reaifinaldecisionsdocument\project

# Activate virtual environment
.venv\Scripts\activate  # Windows
# OR
source .venv/bin/activate  # Mac/Linux

# Run migration
python app/migrations/run_phase_migration.py
```

**Option B: Manual SQL Execution**

If the script fails (due to RPC permissions), run the SQL manually:

1. Open Supabase Dashboard → SQL Editor
2. Copy contents of `app/migrations/003_add_phase_to_token_usage.sql`
3. Execute the SQL
4. Verify success by checking for `phase` column in `token_usage` table

### Step 2: Restart Backend Server

The code changes are already applied. Just restart your backend:

```bash
# Stop current backend (Ctrl+C)
# Start backend again
python backend_runner.py
```

### Step 3: Test the Fixes

1. **Test Rubric Extraction:**
   - Upload a rubric PDF
   - Start grading with a Gemini model
   - Check logs for "✅ Saved rubric token usage"
   - Verify no "cache_creation_input_tokens" errors

2. **Test Assessment:**
   - Complete a grading session
   - Check logs for "✅ Saved token usage for X records"
   - No JSON parse errors should appear

3. **Verify Token Storage:**
   ```sql
   -- In Supabase SQL Editor, run:
   SELECT 
     session_id, 
     model_name, 
     try_index, 
     phase,
     input_tokens, 
     output_tokens, 
     reasoning_tokens,
     cost_estimate
   FROM token_usage
   ORDER BY created_at DESC
   LIMIT 20;
   ```
   
   You should see rows with `phase = 'rubric'` and `phase = 'assessment'`

---

## 🎯 Expected Behavior After Fixes

### Before:
```
ERROR Failed to store rubric result: Could not find 'cache_creation_input_tokens'
ERROR JSON parse error: Invalid \escape: line 39 column 301
```

### After:
```
✅ Saved rubric token usage for pair_0_... (try 1)
✅ Saved token usage for 2 records
✅ Successfully parsed assessment JSON response
```

### Token Storage:

**Before:** Token data scattered, rubric tokens in `rubric_result`, assessment in `token_usage`

**After:** All tokens in `token_usage` table:
| session_id | model_name | try_index | phase | input_tokens | output_tokens | reasoning_tokens |
|------------|------------|-----------|-------|--------------|---------------|------------------|
| uuid-123   | pair_0_... | 1         | rubric| 11675        | 6052          | 0                |
| uuid-123   | pair_0_... | 1         | assessment | 6710   | 10033         | 8627             |

---

## 🔄 Rollback Instructions

If you need to revert the migration:

```bash
python app/migrations/run_phase_migration.py --rollback
```

Or manually execute: `app/migrations/003_add_phase_to_token_usage_ROLLBACK.sql`

---

## 🧪 Testing Checklist

- [ ] Migration completed successfully
- [ ] Backend restarts without errors
- [ ] Rubric extraction works (no cache column errors)
- [ ] JSON parsing works for Gemini models (no escape sequence errors)
- [ ] Token usage data appears in database with both phases
- [ ] Performance Analysis tab shows complete token data
- [ ] Cost estimates are accurate for both phases

---

## 📊 Performance Analysis Updates

The Performance Analysis tab can now query token usage like this:

```typescript
// Get total tokens per model including both phases
const { data } = await supabase
  .from('token_usage')
  .select('model_name, phase, input_tokens, output_tokens, reasoning_tokens, cost_estimate')
  .eq('session_id', sessionId)
  .order('try_index', { ascending: true });

// Group by model and phase for display
const breakdown = data.reduce((acc, row) => {
  const key = `${row.model_name}_${row.phase}`;
  acc[key] = row;
  return acc;
}, {});
```

---

## 🐛 Error Handling Improvements

The new JSON parser provides better error messages:

**Before:**
```json
{"reason": "parse_exception", "error": "Invalid \\escape"}
```

**After:**
```json
{
  "reason": "parse_exception",
  "error": "Invalid \\escape: line 39 column 301",
  "original_error": "...",
  "json_preview": "...",
  "position": 2606,
  "line": 39,
  "column": 301
}
```

---

## 📞 Support

If you encounter issues:

1. Check logs in `logs/` directory
2. Check session logs in `logs/session_<session_id>.log`
3. Verify migration status in Supabase Dashboard
4. Check that `.env` file has correct Supabase credentials

---

## 🎉 What's Improved

✅ **Robust JSON Parsing** - Handles all LLM quirks (markdown, escapes, preambles)  
✅ **Unified Token Storage** - All token data in one table with phase distinction  
✅ **Better Error Messages** - Detailed parse errors for easier debugging  
✅ **Cost Tracking** - Accurate cost breakdown by phase  
✅ **Database Integrity** - No more missing column errors  

---

## Version

- **Date:** October 21, 2025
- **Migration:** 003_add_phase_to_token_usage
- **Status:** ✅ Ready for deployment
