# Complete Fix Summary: Reasoning & Prompt Settings

## Issues Fixed

### 1. ✅ Custom Prompt Settings Not Loading
**Problem**: Backend was using default prompts instead of custom settings from UI
**Solution**: 
- Fixed JSONB parsing from Supabase
- Added comprehensive debug logging
- Settings now properly load and apply

### 2. ✅ Reasoning Configuration Not Being Sent
**Problem**: Reasoning configs weren't reaching the backend
**Solution**:
- Frontend now sends per-model reasoning configurations
- Backend accepts and uses individual reasoning per model
- Debug logs show exact reasoning being used

### 3. ✅ Same Model with Different Reasoning Treated as One
**Problem**: Using same model twice with different reasoning only showed one result
**Solution**:
- Added `instance_id` to differentiate model instances
- Results stored separately for each configuration
- Review page shows all instances distinctly

## What the Logs Now Show

### With Debug Mode (`OPENROUTER_DEBUG=1`):

#### 1. Prompt Settings Loading:
```
------------------------------------------------------------
🔍 Fetching prompt settings from database...
------------------------------------------------------------
📄 Database response: 1 rows found
✅ Templates loaded:
  - System template: 850 chars
  - User template: 120 chars
------------------------------------------------------------
✅ Using custom templates from settings
```

#### 2. Per-Model Reasoning:
```
================================================================================
🔍 LLM REQUEST DETAILS
================================================================================
📝 Session ID: abc123
🤖 Models: [('openai/gpt-5-mini', None), ('openai/gpt-5-mini', 'openai/gpt-5-mini_1_custom')]
🧠 Per-Model Reasoning Configs:
  Model 2 (openai/gpt-5-mini):
    Instance ID: openai/gpt-5-mini_1_custom
    Reasoning: {
      "max_tokens": 2000
    }
```

#### 3. API Calls with Reasoning:
```
------------------------------------------------------------
🚀 OPENROUTER API CALL - Attempt 1
------------------------------------------------------------
🌐 URL: https://openrouter.ai/api/v1/chat/completions
🤖 Model: openai/gpt-5-mini
🧠 Reasoning for this call: {
  "max_tokens": 2000
}
📦 Payload Preview:
{
  "model": "openai/gpt-5-mini",
  "messages": [...],
  "reasoning": {
    "max_tokens": 2000
  }
}
```

## How to Test Everything

### 1. Verify Custom Prompts:
```javascript
// In browser console
fetch('http://127.0.0.1:8000/settings/prompt/debug')
  .then(r => r.json())
  .then(console.log)
```
Should show: `"recommendation": "Settings exist"`

### 2. Test Reasoning Configuration:
1. Create assessment with same model twice
2. Set different reasoning (None vs Custom 2000)
3. Check browser console for model specs
4. Backend logs will show both configurations

### 3. Verify Results Display:
- Review page should show both model instances separately
- Each with its own results and scores

## Key Improvements

| Feature | Before | After |
|---------|--------|-------|
| Custom Prompts | Silently failed, used defaults | Properly loads with debug info |
| Reasoning Config | Not sent to backend | Per-model reasoning sent |
| Same Model Multiple Times | Overwritten results | Separate instance IDs |
| Debug Logging | Minimal, hard to read | Structured with emojis & sections |
| Error Handling | Silent failures | Clear error messages |

## Files Changed Summary

### Backend:
- `app/routers/grade.py` - JSONB parsing, per-model reasoning, better logging
- `app/routers/settings.py` - Debug endpoint, save/load logging
- `app/schemas.py` - Per-model reasoning schema

### Frontend:
- `src/utils/api.ts` - Per-model reasoning specs
- `src/context/AssessmentContext.tsx` - Pass reasoning configs
- `src/pages/Settings.tsx` - Debug logging
- `src/types/index.ts` - Reasoning types

## Quick Checklist

✅ Enable `OPENROUTER_DEBUG=1` in `.env`
✅ Save custom prompts in Settings page
✅ Check `/settings/prompt/debug` endpoint
✅ Test with same model + different reasoning
✅ Verify both results appear in Review page
✅ Check backend logs for reasoning configs

Your app now properly handles:
1. Custom prompt templates from the Settings page
2. Per-model reasoning configurations
3. Multiple instances of the same model with different settings
4. Clear debug logging for troubleshooting

Everything should work as expected!
