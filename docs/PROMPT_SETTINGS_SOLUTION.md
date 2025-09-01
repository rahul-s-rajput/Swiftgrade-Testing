# Troubleshooting Prompt Settings

## The Issue
The backend is using default prompts instead of your custom settings. This is happening because the settings either aren't saved properly or aren't being retrieved correctly from the Supabase database.

## Solution Steps

### 1. Enable Debug Mode
Add to your `.env` file:
```
OPENROUTER_DEBUG=1
```

### 2. Save Your Custom Prompts Through the UI

1. Go to the **Settings** page in your app
2. Paste your custom prompts:

**System Template:**
```
<Role>
You are a teacher whose job is to grade student assessments.
</Role>

<Task>
You will be given three inputs:
- `answer_key`
- `questions_list`
- `student_assessments`
For each student in `student_assessments`, you must:
1. Extract the student's `first_name`, `last_name` and `Student_ID`.
2. For each question in `questions_list`, assign a `mark` and provide `feedback`.
3. Format the final output for each student as a single JSON object.
</Task>

<Instructions>
Follow the detailed grading instructions and feedback rubric precisely.
</Instructions>

<Answer_Key>
Here are the answer key pages. Use these to determine correct answers and any specific grading criteria:
[Answer key]
</Answer_Key>

<Question_List>
Here are the specific questions to grade. Only grade these questions in the student's assessment:
[Question list]
</Question_List>
```

**User Template:**
```
<Student_Assessments>
Here are the pages of the student's test:
[Student assessment]
</Student_Assessments>
```

3. Click **Save Settings**
4. Check the browser console (F12) for:
   - `💾 Saving prompt settings...`
   - `✅ Settings saved successfully`

### 3. Verify in Supabase Dashboard

1. Go to your Supabase dashboard
2. Navigate to the SQL Editor
3. Run this query:
```sql
SELECT * FROM app_settings WHERE key = 'prompt_settings';
```

You should see a row with:
- `key`: "prompt_settings"
- `value`: A JSON object containing your templates
- `updated_at`: Recent timestamp

### 4. Test a Grading Session

Create a new assessment and check the backend logs. You should see:

**Success (using custom templates):**
```
------------------------------------------------------------
🔍 Fetching prompt settings from database...
------------------------------------------------------------
📄 Database response: 1 rows found
📄 Extracted templates:
  - System template: 850 chars (is None: False)
  - User template: 120 chars (is None: False)
------------------------------------------------------------
✅ Using custom templates from settings
------------------------------------------------------------
```

**Failure (using defaults):**
```
⚠️ Using default fallback templates
  - sys_template is None: True
  - user_template is None: True
```

## What's Been Fixed

### Backend Improvements (`grade.py`):
1. **Better JSONB handling** - Properly parses JSONB data whether it comes as dict or string
2. **Validation** - Ensures templates are non-empty strings
3. **Detailed logging** - Shows exact data types and content at each step
4. **Error recovery** - Falls back gracefully if parsing fails

### Frontend Improvements (`Settings.tsx`):
1. **Console logging** - Shows what's being saved/loaded
2. **Better feedback** - More informative success message
3. **Warning for defaults** - Alerts when using default templates

## Browser Console Test

You can test the settings directly in your browser console:

```javascript
// Test loading settings
fetch('http://127.0.0.1:8000/settings/prompt')
  .then(r => r.json())
  .then(data => {
    console.log('Current settings:', data);
    console.log('System template length:', data.system_template?.length);
    console.log('User template length:', data.user_template?.length);
  });

// Test saving settings
fetch('http://127.0.0.1:8000/settings/prompt', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    system_template: "TEST SYSTEM",
    user_template: "TEST USER"
  })
})
  .then(r => r.json())
  .then(data => console.log('Save result:', data))
  .catch(e => console.error('Save failed:', e));
```

## Common Issues & Solutions

### Issue: "No prompt settings found in database"
**Solution:** Save settings through the UI Settings page

### Issue: Templates showing as None
**Solution:** 
1. Check that the Settings page shows your templates
2. Re-save them
3. Check Supabase for the stored data

### Issue: JSONB parsing error
**Solution:** The updated code handles this automatically by trying to parse strings as JSON

### Issue: Settings save but don't load
**Solution:** 
1. Check browser console for errors
2. Verify the backend is running
3. Check CORS settings if needed

## Direct Database Fix (if needed)

If the UI isn't working, you can update directly in Supabase:

```sql
UPDATE app_settings 
SET value = jsonb_build_object(
  'system_template', '<Your system template here>',
  'user_template', '<Your user template here>'
),
updated_at = NOW()
WHERE key = 'prompt_settings';
```

If the row doesn't exist:
```sql
INSERT INTO app_settings (key, value) 
VALUES (
  'prompt_settings',
  jsonb_build_object(
    'system_template', '<Your system template here>',
    'user_template', '<Your user template here>'
  )
);
```

## Summary

The issue should now be resolved with the improved error handling and logging. The key points:

1. **Save through the UI** - Use the Settings page to save your custom prompts
2. **Check console logs** - Both browser and backend logs now show detailed information
3. **Verify in database** - Use Supabase dashboard to confirm data is stored
4. **Test with debug mode** - `OPENROUTER_DEBUG=1` shows exactly what's happening

Your custom prompts will be used once they're properly saved to the database through the Settings page.
