# Fix for Per-Model Reasoning Configuration

## Problem Identified
Looking at your logs, the reasoning configuration was not being sent to the backend:
- The payload preview showed no `"reasoning"` field
- Same model with different reasoning configs were treated as one instance
- Frontend only showed one result instead of separate results for each configuration

## Solution Implemented

### 1. Per-Model Reasoning Support
Updated the system to support different reasoning configurations for each model instance:

#### Frontend Changes (`src/utils/api.ts`):
- Creates model specs with individual reasoning configurations
- Generates unique `instance_id` for same model with different reasoning (e.g., `openai/gpt-5-mini_0_none`, `openai/gpt-5-mini_1_custom`)
- Passes reasoning configuration per model instance

#### Backend Changes (`app/routers/grade.py`):
- Accepts per-model reasoning in `GradeModelSpec`
- Uses instance-specific reasoning for each API call
- Stores results with `instance_id` to differentiate same model with different configs

### 2. Schema Updates (`app/schemas.py`):
```python
class GradeModelSpec(BaseModel):
    name: str
    tries: Optional[int] = None
    reasoning: Optional[Dict[str, Any]] = None  # Per-model reasoning
    instance_id: Optional[str] = None  # Unique identifier for this instance
```

### 3. Debug Logging Enhanced
Backend now shows per-model reasoning:
```
🧠 Per-Model Reasoning Configs:
  Model 1 (openai/gpt-5-mini):
    Instance ID: openai/gpt-5-mini_0_none
    Reasoning: None
  Model 2 (openai/gpt-5-mini):
    Instance ID: openai/gpt-5-mini_1_custom
    Reasoning: {
      "max_tokens": 2000
    }
```

## How It Works Now

When you select the same model twice with different reasoning:

1. **Frontend**: Creates two distinct model specifications:
   ```javascript
   [
     { 
       name: "openai/gpt-5-mini", 
       instance_id: "openai/gpt-5-mini_0_none"
     },
     { 
       name: "openai/gpt-5-mini", 
       instance_id: "openai/gpt-5-mini_1_custom",
       reasoning: { max_tokens: 2000 }
     }
   ]
   ```

2. **Backend**: Makes separate API calls with appropriate reasoning for each

3. **Database**: Stores results with unique identifiers so they don't overwrite each other

4. **Review Page**: Shows both results separately

## Testing

1. Create an assessment with:
   - Same model selected twice
   - Different reasoning configs (e.g., None and Custom 2000 tokens)

2. Check browser console for:
   ```
   🧠 Sending model-specific reasoning configurations:
     Model 1: openai/gpt-5-mini
       No reasoning
     Model 2: openai/gpt-5-mini
       Reasoning: {"max_tokens":2000}
       Instance ID: openai/gpt-5-mini_1_custom
   ```

3. Backend logs with `OPENROUTER_DEBUG=1` will show:
   - Per-model reasoning configs
   - Separate API calls with correct reasoning
   - Instance IDs for differentiation

4. Review page will display both results separately

## Key Benefits

✅ **Per-model reasoning**: Each model instance can have its own reasoning configuration
✅ **Same model, different configs**: Can test same model with different reasoning levels
✅ **Proper differentiation**: Results stored and displayed separately
✅ **Clear debugging**: Logs show exactly what reasoning is sent per model

## Files Modified

- `app/schemas.py` - Added per-model reasoning fields
- `app/routers/grade.py` - Handle per-model reasoning and instance IDs
- `src/utils/api.ts` - Create model specs with reasoning
- `src/context/AssessmentContext.tsx` - Pass per-model reasoning configs

The system now properly handles multiple instances of the same model with different reasoning configurations!
