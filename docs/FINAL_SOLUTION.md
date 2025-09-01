# Complete Solution: Custom Prompts Not Loading

## Problem Summary
Your custom prompt settings from the Settings page weren't being used during grading. The backend was falling back to default prompts.

## Root Cause
The Supabase JSONB data wasn't being parsed correctly, causing the templates to be `None` even when they existed in the database.

## Fixes Implemented

### 1. Backend JSONB Handling (`app/routers/grade.py`)
- Added robust JSONB parsing that handles both dict and string formats
- Added validation to ensure templates are non-empty strings
- Enhanced debug logging to show exact data types and parsing steps
- Proper error handling with fallback to defaults

### 2. Settings Management (`app/routers/settings.py`)
- Added debug endpoint: `/settings/prompt/debug` for troubleshooting
- Enhanced logging for save/load operations
- Better error messages

### 3. Frontend Debugging (`src/pages/Settings.tsx`)
- Added console logging for save/load operations
- Shows template lengths and previews
- Better success/error messages

## How to Use Your Custom Prompts

### Step 1: Enable Debug Mode (Optional but Recommended)
```bash
# In your .env file
OPENROUTER_DEBUG=1
```

### Step 2: Save Your Custom Prompts
1. Go to the **Settings** page in your app
2. Paste your custom templates
3. Click **Save Settings**
4. Check browser console for `✅ Settings saved successfully`

### Step 3: Verify Settings Are Stored
Open browser console and run:
```javascript
fetch('http://127.0.0.1:8000/settings/prompt/debug')
  .then(r => r.json())
  .then(console.log)
```

You should see:
```json
{
  "status": "found",
  "checks": {
    "has_system_template": true,
    "has_user_template": true,
    "system_template_length": 850,
    "user_template_length": 120
  },
  "recommendation": "Settings exist"
}
```

### Step 4: Test Grading
Create a new assessment. With debug mode enabled, backend logs will show:
```
✅ Using custom templates from settings
```

## What Changed in Your Code

### Backend Changes:
1. **Improved JSONB parsing** - Handles Supabase JSONB whether it comes as dict or string
2. **Better validation** - Ensures templates are valid non-empty strings
3. **Debug endpoint** - `/settings/prompt/debug` for troubleshooting
4. **Comprehensive logging** - Shows each step of template loading

### Frontend Changes:
1. **Console logging** - Shows what's being saved/loaded
2. **Better feedback** - Clear success/error messages

## Troubleshooting Guide

### Check Settings Status
```bash
# In browser console
fetch('http://127.0.0.1:8000/settings/prompt/debug').then(r => r.json()).then(console.log)
```

### Common Issues:

| Issue | Solution |
|-------|----------|
| "no_settings" status | Save settings through UI |
| Templates are empty | Re-paste and save in Settings page |
| Backend uses defaults | Check debug logs for parsing errors |

### Direct Database Check (Supabase Dashboard)
```sql
SELECT * FROM app_settings WHERE key = 'prompt_settings';
```

## No Manual Scripts Needed!

Since you're using Supabase with a proper UI:
1. **Just use the Settings page** - No need for manual scripts
2. **Database is automatic** - Supabase handles JSONB storage
3. **Debug endpoint helps** - `/settings/prompt/debug` shows status

## Summary

Your custom prompts will now work correctly because:
1. ✅ JSONB parsing is fixed
2. ✅ Validation ensures non-empty templates
3. ✅ Debug logging shows what's happening
4. ✅ Settings page properly saves/loads

Just save your templates through the Settings page and they'll be used automatically!
