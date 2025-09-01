# Prompt Settings Issue - Diagnosis & Solution

## Problem Identified
The backend is using default/fallback prompts instead of the custom prompts configured in the Settings panel.

### Root Causes

1. **Database Connection Issue**: The prompts may not be saved properly to the database
2. **Silent Exception Handling**: The code catches exceptions without logging, making it hard to diagnose
3. **Data Retrieval Issue**: The query might not be returning data in the expected format

## Solution Implemented

### 1. Enhanced Debug Logging
Added comprehensive logging throughout the prompt loading process:

```python
# In grade.py - _build_messages function
- Logs when fetching settings from database
- Shows raw database response
- Indicates whether custom or default templates are used
- Shows template character counts and previews
```

### 2. Fixed Query Consistency
Updated the database query to match between files:
- Changed from `select("value")` to `select("key,value")` for consistency

### 3. Added Debug Scripts

#### `test_database_settings.py`
Tests the database connection and prompt retrieval:
```bash
python test_database_settings.py
```

#### `save_custom_prompts.py`
Manually saves your custom prompts to the database:
```bash
python save_custom_prompts.py
```

## How to Fix the Issue

### Step 1: Enable Debug Mode
Add to your `.env` file:
```
OPENROUTER_DEBUG=1
```

### Step 2: Save Custom Prompts
Run the script to ensure prompts are in the database:
```bash
python save_custom_prompts.py
```

Expected output:
```
================================================================================
💾 SAVING CUSTOM PROMPT SETTINGS
================================================================================
✅ Settings saved successfully!
✅ Verification successful! Templates match.
```

### Step 3: Verify in UI
1. Go to Settings page in the UI
2. Check that your custom prompts are displayed
3. If not visible, paste them and click Save

### Step 4: Test Grading
1. Create a new assessment
2. Check backend logs for:
```
✅ Using custom templates from settings
```

If you see:
```
⚠️ Using default fallback templates
```
Then check the debug logs above it for the reason.

## Troubleshooting

### If prompts aren't loading:

1. **Check database connection**:
   ```bash
   python test_database_settings.py
   ```

2. **Look for error messages** in backend logs:
   - `❌ Failed to load prompt settings from database`
   - `⚠️ No prompt settings found in database`

3. **Verify Supabase setup**:
   - Ensure `app_settings` table exists
   - Check that it has `key` and `value` columns
   - `value` column should be JSONB type

4. **Manual database check**:
   - Go to Supabase dashboard
   - Run SQL query:
   ```sql
   SELECT * FROM app_settings WHERE key = 'prompt_settings';
   ```
   - Verify the value contains your templates

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "No prompt settings found in database" | Run `save_custom_prompts.py` |
| Templates showing as `None` | Check that Settings page saved successfully |
| Database connection error | Verify Supabase credentials in `.env` |
| Templates not matching | Clear browser cache and re-save in Settings |

## Backend Log Examples

### Successful Custom Template Loading:
```
------------------------------------------------------------
🔍 Fetching prompt settings from database...
------------------------------------------------------------
📄 Database response: 1 rows found
📦 Raw data: {
  "key": "prompt_settings",
  "value": {
    "system_template": "<Role>...",
    "user_template": "<Student_Assessments>..."
  }
}
✅ Templates loaded:
  - System template: 850 chars
  - User template: 120 chars
------------------------------------------------------------
✅ Using custom templates from settings
------------------------------------------------------------
```

### Failed Loading (Falls back to defaults):
```
------------------------------------------------------------
🔍 Fetching prompt settings from database...
------------------------------------------------------------
❌ Failed to load prompt settings from database: [error message]
------------------------------------------------------------
⚠️ Using default fallback templates
  - sys_template is None: True
  - user_template is None: True
------------------------------------------------------------
```

## Files Modified

1. **Backend (`app/routers/grade.py`)**:
   - Added debug logging for template loading
   - Fixed query to use `select("key,value")`
   - Shows which templates are being used

2. **Backend (`app/routers/settings.py`)**:
   - Added logging for save/load operations
   - Shows template sizes and previews

3. **New Scripts**:
   - `test_database_settings.py` - Database testing
   - `save_custom_prompts.py` - Manual prompt saving

## Next Steps

1. Run `save_custom_prompts.py` to ensure prompts are saved
2. Enable `OPENROUTER_DEBUG=1` in `.env`
3. Test a grading session
4. Check logs for "✅ Using custom templates from settings"

If issues persist, check the database directly in Supabase dashboard and verify the `app_settings` table structure.
