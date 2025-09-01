# Reasoning Configuration Implementation

## Overview
This document describes the implementation of reasoning configuration support for AI models in the mark grading testing app.

## Features Implemented

### 1. Frontend Reasoning Configuration
- **Per-model reasoning settings**: Each selected model can have its own reasoning configuration
- **Reasoning levels supported**:
  - `none`: No reasoning (default)
  - `low`: Low effort reasoning
  - `medium`: Medium effort reasoning  
  - `high`: High effort reasoning
  - `custom`: Custom token count (min 256 tokens)

### 2. Backend Integration
- Reasoning configuration is now properly passed from frontend to backend
- Backend correctly forwards reasoning settings to OpenRouter API
- Smart mapping between effort-based and token-based reasoning based on model capabilities

### 3. Enhanced Debug Logging
When `OPENROUTER_DEBUG=1` is set in the `.env` file, the backend now provides:

#### Structured Request Logging
```
================================================================================
🔍 LLM REQUEST DETAILS
================================================================================
📝 Session ID: abc123
🤖 Models: ['anthropic/claude-3.5-sonnet']
🔁 Default Tries: 3
🧠 Reasoning Config: {
  "effort": "high"
}
--------------------------------------------------------------------------------
💬 SYSTEM MESSAGE:
[System prompt content...]
--------------------------------------------------------------------------------
👤 USER MESSAGE:
[User prompt content...]
================================================================================
```

#### API Call Tracking
```
------------------------------------------------------------
🚀 OPENROUTER API CALL - Attempt 1
------------------------------------------------------------
🌐 URL: https://openrouter.ai/api/v1/chat/completions
🤖 Model: anthropic/claude-3.5-sonnet
📦 Payload Preview:
[Pretty-printed JSON payload]
------------------------------------------------------------
✅ OPENROUTER RESPONSE
📊 Status Code: 200
📄 Response Preview:
[Pretty-printed JSON response]
------------------------------------------------------------
```

#### Image Preflight Checks
```
------------------------------------------------------------
🖼️ IMAGE URL PREFLIGHT CHECKS
------------------------------------------------------------
✅ Image 1: Status 200 - https://storage.example.com/image1.jpg
✅ Image 2: Status 200 - https://storage.example.com/image2.jpg
------------------------------------------------------------
```

#### Error Reporting
```
------------------------------------------------------------
❌ OPENROUTER API ERROR - Attempt 2
------------------------------------------------------------
📊 Status Code: 429
📄 Error Details: Rate limit exceeded
📄 Response Body:
{
  "error": {
    "message": "Rate limit exceeded",
    "type": "rate_limit_error"
  }
}
------------------------------------------------------------
```

## How Reasoning Works

### Model-Specific Reasoning Types

#### Effort-Based Models
These models support `effort` parameter with values: `low`, `medium`, `high`
- Anthropic (Claude) models
- Mistral Magistral models
- Google Gemini 2.5/2.0 models
- Z-AI GLM models

#### Token-Based Models  
These models support `max_tokens` parameter for reasoning
- OpenAI models
- DeepSeek models
- Qwen thinking models

#### Automatic Mapping
The system automatically converts between formats:
- If a token-based model receives effort levels, they're mapped to token counts:
  - `low` → 1024 tokens
  - `medium` → 8192 tokens
  - `high` → 32768 tokens
- If an effort-based model receives custom tokens, it's mapped to `high` effort

## Testing Reasoning Configuration

### 1. Enable Debug Logging
Add to your `.env` file:
```
OPENROUTER_DEBUG=1
```

### 2. Use the Test Script
Run the provided test script:
```bash
python test_reasoning.py
```

### 3. Monitor Frontend Console
The frontend logs reasoning configuration when creating assessments:
```
📊 Reasoning Configuration: {effort: "high"}
🤖 Models: ['anthropic/claude-3.5-sonnet']
🧠 Frontend Reasoning: [{level: 'high'}]
```

### 4. Check Backend Logs
With debug mode enabled, the backend will show:
- Exact reasoning configuration received
- How it's passed to OpenRouter
- Model responses with reasoning applied

## File Changes Summary

### Frontend Files Modified:
- `src/types/index.ts` - Added ReasoningConfig types
- `src/pages/NewAssessment.tsx` - Pass reasoning to context
- `src/context/AssessmentContext.tsx` - Convert and forward reasoning
- `src/utils/api.ts` - API layer accepts reasoning parameter

### Backend Files Modified:
- `app/routers/grade.py` - Enhanced debug logging and reasoning handling

### New Files:
- `test_reasoning.py` - Test script for reasoning configurations
- `REASONING_IMPLEMENTATION.md` - This documentation

## Troubleshooting

### Reasoning Not Working?
1. Check frontend console for reasoning configuration logs
2. Enable `OPENROUTER_DEBUG=1` in backend
3. Verify model supports reasoning (check `supportsReasoning` in frontend)
4. Ensure reasoning level is not 'none'

### Debug Tips:
- Frontend: Open browser console to see reasoning config
- Backend: Set `OPENROUTER_DEBUG=1` for detailed logs
- Use test script to verify configuration format

## Future Enhancements
- Support different reasoning configs per model in same batch
- Add reasoning cost estimates in UI
- Store reasoning config in database for session replay
- Add reasoning performance metrics to results
