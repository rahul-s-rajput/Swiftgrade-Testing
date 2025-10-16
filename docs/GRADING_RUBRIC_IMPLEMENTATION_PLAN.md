# Grading Rubric Feature - Implementation Plan

**Feature Overview:** Add grading rubric functionality where each assessment uses model pairs (rubric model + assessment model). The rubric model processes grading rubric images first, then its output is passed to the assessment model.

**Start Date:** [To be filled]
**Target Completion:** [To be filled]
**Status:** 🔴 Not Started

---

## Phase 1: Database Schema Changes
**Estimated Time:** 30 minutes

### 1.1 Create Migration Script
- [x] Create new migration file: `app/migrations/add_grading_rubric_support.sql`
- [x] Add migration to create `rubric_result` table
- [x] Add migration to update `image` table role constraint
- [x] Add migration to update `session` table with new columns
- [x] Test migration on development database

**Files to Create:**
- `app/migrations/add_grading_rubric_support.sql`

**SQL Changes:**
```sql
-- Add grading rubric columns to session table
ALTER TABLE session ADD COLUMN IF NOT EXISTS rubric_model TEXT;
ALTER TABLE session ADD COLUMN IF NOT EXISTS assessment_model TEXT;

-- New table for grading rubric results
CREATE TABLE IF NOT EXISTS rubric_result (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES session(id),
  model_name TEXT NOT NULL,
  try_index INTEGER NOT NULL,
  rubric_response TEXT,
  raw_output JSONB,
  validation_errors JSONB,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT unique_rubric_per_attempt UNIQUE (session_id, model_name, try_index)
);

-- Update image table role constraint
ALTER TABLE image DROP CONSTRAINT IF EXISTS image_role_check;
ALTER TABLE image ADD CONSTRAINT image_role_check 
  CHECK (role IN ('student', 'answer_key', 'grading_rubric'));

-- Create index for rubric results
CREATE INDEX IF NOT EXISTS idx_rubric_result_session ON rubric_result(session_id);
CREATE INDEX IF NOT EXISTS idx_rubric_result_model_try ON rubric_result(model_name, try_index);
```

---

## Phase 2: Backend - Schemas & Models
**Estimated Time:** 1 hour

### 2.1 Update Backend Schemas
- [x] Open `app/schemas.py`
- [x] Add `ModelPairSpec` class for rubric + assessment model pairs
- [x] Add `RubricPromptSettingsReq` schema
- [x] Add `RubricPromptSettingsRes` schema
- [x] Update `GradeSingleReq` to use `model_pairs` instead of `models`
- [x] Add backward compatibility handling for old `models` field
- [x] Test schema validation

**Files to Modify:**
- `app/schemas.py`

**Code Changes:**
```python
# Add new schemas
class ModelPairSpec(BaseModel):
    rubric_model: ModelSpec
    assessment_model: ModelSpec
    instance_id: str | None = None

class RubricPromptSettingsReq(BaseModel):
    system_template: str
    user_template: str

class RubricPromptSettingsRes(BaseModel):
    system_template: str
    user_template: str

# Update existing
class GradeSingleReq(BaseModel):
    session_id: str
    model_pairs: List[ModelPairSpec] | None = None  # NEW
    models: List[ModelSpec] | None = None  # Keep for backward compat
    default_tries: int | None = 1
    reasoning: Dict[str, Any] | None = None
```

---

## Phase 3: Backend - Settings Router
**Estimated Time:** 1 hour

### 3.1 Add Rubric Prompt Settings Endpoints
- [x] Open `app/routers/settings.py`
- [x] Add `DEFAULT_RUBRIC_SYSTEM_TEMPLATE` constant
- [x] Add `DEFAULT_RUBRIC_USER_TEMPLATE` constant
- [x] Add `get_rubric_prompt_settings()` endpoint
- [x] Add `put_rubric_prompt_settings()` endpoint
- [x] Add `debug_rubric_prompt_settings()` endpoint (optional)
- [x] Test endpoints with Postman/curl

**Files to Modify:**
- `app/routers/settings.py`

**New Endpoints:**
- `GET /settings/rubric-prompt`
- `PUT /settings/rubric-prompt`
- `GET /settings/rubric-prompt/debug` (optional)

**Default Templates:**
```python
DEFAULT_RUBRIC_SYSTEM_TEMPLATE = """
<Role>
You are a grading rubric analyzer whose job is to extract and structure grading criteria.
</Role>

<Task>
You will be given grading rubric images. Your task is to:
1. Extract all grading criteria and rubric details
2. Organize them by question
3. Return a clear, structured rubric text
</Task>

<Grading_Rubric_Images>
[Grading rubric images]
</Grading_Rubric_Images>

<Question_List>
[Question list]
</Question_List>
"""

DEFAULT_RUBRIC_USER_TEMPLATE = """
Please analyze the grading rubric images and extract all grading criteria for each question.
"""
```

---

## Phase 4: Backend - Grade Router (Rubric Logic)
**Estimated Time:** 3-4 hours

### 4.1 Add Rubric Message Building Function
- [x] Open `app/routers/grade.py`
- [x] Create `_build_rubric_messages()` function
- [x] Load rubric templates from Supabase
- [x] Support placeholders: `[Grading rubric images]`, `[Question list]`
- [x] Handle image URL encoding
- [x] Test message building

**Files to Modify:**
- `app/routers/grade.py`

**Function Signature:**
```python
def _build_rubric_messages(
    rubric_urls: List[str],
    questions: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Build OpenRouter chat messages for grading rubric analysis."""
    pass
```

### 4.2 Add Rubric LLM Call Function
- [x] Create `_call_rubric_llm()` function
- [x] Call `_call_openrouter()` with rubric messages
- [x] Parse rubric response to extract text
- [x] Store rubric result in `rubric_result` table
- [x] Handle errors gracefully
- [x] Add debug logging
- [x] Test with actual OpenRouter API

**Function Signature:**
```python
async def _call_rubric_llm(
    client: httpx.AsyncClient,
    model: str,
    rubric_urls: List[str],
    questions: List[Dict[str, Any]],
    reasoning: Dict[str, Any] | None,
    session_id: str,
    try_index: int,
    instance_id: str | None = None
) -> str:
    """Call grading rubric model and return parsed rubric text."""
    pass
```

### 4.3 Update Assessment Message Building
- [x] Update `_build_messages()` signature to accept `rubric_text` parameter
- [x] Add new placeholder `[Grading Rubric]` support
- [x] Replace placeholder with actual rubric text in system template
- [x] Ensure backward compatibility (rubric_text=None)
- [x] Test message building with and without rubric

**Updated Signature:**
```python
def _build_messages(
    student_urls: List[str],
    key_urls: List[str],
    questions: List[Dict[str, Any]],
    rubric_text: str | None = None  # NEW PARAMETER
) -> List[Dict[str, Any]]:
    """Build OpenRouter chat messages with optional rubric."""
    pass
```

### 4.4 Refactor grade_single Endpoint
- [x] Update `grade_single()` to load rubric images from database
- [x] Add logic to handle both `model_pairs` and legacy `models` field
- [x] Expand model pairs into tasks (rubric + assessment for each try)
- [x] Create async task function that:
  - [x] First calls rubric LLM
  - [x] Then calls assessment LLM with rubric output
  - [x] Handles errors at each step
- [x] Update result storage to include rubric responses
- [x] Update token usage tracking for both calls
- [x] Add comprehensive logging
- [x] Test with single pair
- [x] Test with multiple pairs
- [x] Test error scenarios

**Key Changes in grade_single:**
```python
@router.post("/grade/single", response_model=GradeSingleRes)
async def grade_single(payload: GradeSingleReq) -> GradeSingleRes:
    # Load ALL image types including rubric
    rubric_urls = [r["url"] for r in imgs.data if r.get("role") == "grading_rubric"]
    
    # Handle both new model_pairs and legacy models
    if payload.model_pairs:
        # New logic with pairs
        pass
    elif payload.models:
        # Legacy logic (backward compat)
        pass
    
    async def run_task(rubric_model, assessment_model, try_index, ...):
        # Step 1: Call rubric LLM
        rubric_text = await _call_rubric_llm(...)
        
        # Step 2: Call assessment LLM with rubric
        messages = _build_messages(..., rubric_text=rubric_text)
        assessment_data = await _call_openrouter(...)
        
        return (rubric_model, assessment_model, try_index, rubric_text, assessment_data)
```

---

## Phase 5: Backend - Results Router
**Estimated Time:** 1 hour

### 5.1 Add Rubric Results Endpoint
- [x] Open `app/routers/results.py`
- [x] Add `get_rubric_results()` endpoint
- [x] Query `rubric_result` table by session_id
- [x] Return structured rubric results
- [x] Test endpoint

**Files to Modify:**
- `app/routers/results.py`

**New Endpoint:**
- `GET /results/{session_id}/rubric`

---

## Phase 6: Frontend - Type Definitions
**Estimated Time:** 45 minutes

### 6.1 Update TypeScript Types
- [x] Open `src/types/index.ts`
- [x] Add `ModelPair` interface
- [x] Update `Assessment` interface to include `modelPairs` and `rubricImages`
- [x] Update `ModelResult` interface to include `rubricModel` and `assessmentModel`
- [x] Update `Attempt` interface to include `rubricResponse`
- [x] Keep legacy fields for backward compatibility
- [ ] Run type checking: `npm run type-check`

**Files to Modify:**
- `src/types/index.ts`

**New/Updated Types:**
```typescript
export interface ModelPair {
  rubricModel: string;
  assessmentModel: string;
  rubricReasoning?: ReasoningConfig;
  assessmentReasoning?: ReasoningConfig;
  instanceId?: string;
}

export interface Assessment {
  // ... existing fields
  rubricImages: File[];  // NEW
  modelPairs: ModelPair[];  // NEW (replaces selectedModels for new assessments)
  selectedModels: string[];  // Keep for backward compat
  // ... rest
}

export interface ModelResult {
  rubricModel?: string;  // NEW
  assessmentModel?: string;  // NEW
  model: string;  // Keep for backward compat
  // ... existing fields
}

export interface Attempt {
  // ... existing fields
  rubricResponse?: string;  // NEW
  // ... rest
}
```

---

## Phase 7: Frontend - API Utils
**Estimated Time:** 45 minutes

### 7.1 Add Rubric API Functions
- [ ] Open `src/utils/api.ts`
- [ ] Add `RubricPromptSettingsRes` interface
- [ ] Add `getRubricPromptSettings()` function
- [ ] Add `putRubricPromptSettings()` function
- [ ] Update `registerImage()` to support 'grading_rubric' role
- [ ] Update `gradeSingleWithRetry()` to send model pairs
- [ ] Add `getRubricResults()` function
- [ ] Test API calls

**Files to Modify:**
- `src/utils/api.ts`

**New Functions:**
```typescript
export interface RubricPromptSettingsRes {
  system_template: string;
  user_template: string;
}

export const getRubricPromptSettings = () => 
  getJSON<RubricPromptSettingsRes>(`/settings/rubric-prompt`);

export const putRubricPromptSettings = (body: RubricPromptSettingsRes) =>
  fetch(`${API_BASE}/settings/rubric-prompt`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json());

export const getRubricResults = (session_id: string) =>
  getJSON<RubricResultsRes>(`/results/${session_id}/rubric`);
```

---

## Phase 8: Frontend - Settings Page
**Estimated Time:** 1 hour

### 8.1 Add Rubric Prompt Settings Tab
- [x] Open `src/pages/Settings.tsx`
- [x] Add 'rubric-prompt' tab state
- [x] Add state for rubric system and user templates
- [x] Create `loadRubricPromptSettings()` function
- [x] Create `onSaveRubricPrompt()` function
- [x] Add tab navigation button
- [x] Add form with two textareas (system & user templates)
- [x] Add save/reset buttons
- [x] Wire up API calls
- [x] Test save and load functionality
- [x] Add validation and error handling

**Files to Modify:**
- `src/pages/Settings.tsx`

**UI Components:**
```typescript
// New state
const [rubricSystemTemplate, setRubricSystemTemplate] = useState('');
const [rubricUserTemplate, setRubricUserTemplate] = useState('');

// New tab
<button onClick={() => setActiveTab('rubric-prompt')}>
  Grading Rubric Prompts
</button>

// New form section
{activeTab === 'rubric-prompt' && (
  <form onSubmit={onSaveRubricPrompt}>
    <textarea
      label="Rubric System Template"
      value={rubricSystemTemplate}
      onChange={...}
      placeholder="[Grading rubric images], [Question list]"
    />
    <textarea
      label="Rubric User Template"
      value={rubricUserTemplate}
      onChange={...}
    />
    <button type="submit">Save Rubric Settings</button>
  </form>
)}
```

---

## Phase 9: Frontend - NewAssessment Page
**Estimated Time:** 3 hours

### 9.1 Update Form State
- [x] Open `src/pages/NewAssessment.tsx`
- [x] Add `rubricImages` to form state
- [x] Add `modelPairs` to form state (array of {rubric, assessment})
- [x] Add state for rubric reasoning configs
- [x] Add state for assessment reasoning configs
- [x] Update validation to check model pairs

**Files to Modify:**
- `src/pages/NewAssessment.tsx`

### 9.2 Add Rubric Images Upload Section
- [x] Add new FileUpload component for rubric images
- [x] Add validation error display
- [x] Style to match existing uploads
- [x] Add helper text
- [x] Test file upload functionality

**UI Component:**
```typescript
<div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6">
  <FileUpload
    label="Upload Grading Rubric Images"
    files={formData.rubricImages}
    onChange={(files) => setFormData({ ...formData, rubricImages: files })}
  />
  <p className="text-xs text-slate-500 mt-2">
    Upload images of the grading rubric that will guide the AI assessment
  </p>
</div>
```

### 9.3 Add Dual Model Selector UI
- [x] Add first MultiSelect for rubric models
- [x] Add second MultiSelect for assessment models
- [x] Implement pairing logic (indices must match)
- [x] Add visual indicators showing pairs
- [x] Add reasoning configuration for BOTH model types
- [x] Handle model removal (remove from both selectors)
- [x] Handle model reordering
- [x] Add clear visual distinction between rubric and assessment selectors
- [x] Test pairing logic thoroughly

**UI Components:**
```typescript
{/* Rubric Model Selector */}
<div className="space-y-2">
  <label className="block text-sm font-semibold text-slate-700">
    Select Grading Rubric Models
  </label>
  <MultiSelect
    label="Grading Rubric Models"
    options={imageModels}
    selectedValues={formData.modelPairs.map(p => p.rubric)}
    onChange={handleRubricModelChange}
    allowDuplicates
    maxPerOption={4}
    shouldShowChipMenuAt={(id, index) => !!modelInfoById?.[id]?.supportsReasoning}
    getChipBadgeAt={(id, index) => /* reasoning badge */}
    onChipMenuRequestAt={/* reasoning menu */}
  />
  <p className="text-xs text-slate-500">
    These models will analyze the grading rubric first
  </p>
</div>

{/* Assessment Model Selector */}
<div className="space-y-2">
  <label className="block text-sm font-semibold text-slate-700">
    Select Assessment Models (pairs with rubric models above)
  </label>
  <MultiSelect
    label="Assessment Models"
    options={imageModels}
    selectedValues={formData.modelPairs.map(p => p.assessment)}
    onChange={handleAssessmentModelChange}
    allowDuplicates
    maxPerOption={4}
    // ... similar props
  />
  <p className="text-xs text-slate-500">
    These models will grade using the rubric from paired models above
  </p>
</div>

{/* Visual Pair Indicator */}
<div className="mt-4 p-4 bg-blue-50 rounded-lg">
  <h4 className="text-sm font-semibold text-slate-700 mb-2">Model Pairs:</h4>
  {formData.modelPairs.map((pair, idx) => (
    <div key={idx} className="flex items-center gap-2 text-sm text-slate-600">
      <span className="font-medium">Pair {idx + 1}:</span>
      <span>{pair.rubric}</span>
      <span>→</span>
      <span>{pair.assessment}</span>
    </div>
  ))}
</div>
```

### 9.4 Update Form Validation
- [x] Add validation for rubric images (optional or required?)
- [x] Add validation for model pairs (at least one pair)
- [x] Update error messages
- [x] Test validation

### 9.5 Update Form Submission
- [x] Update `handleSubmit()` to include rubric images
- [x] Register rubric images with backend
- [x] Send model pairs instead of single models
- [x] Update assessment creation logic
- [x] Add error handling for rubric image upload
- [x] Test end-to-end submission

---

## Phase 10: Frontend - Review Page
**Estimated Time:** 3 hours

### 10.1 Add Sub-Tab Navigation
- [x] Open `src/pages/Review.tsx`
- [x] Add `questionTab` state: 'both' | 'rubric' | 'feedback'
- [x] Create sub-tab navigation UI
- [x] Add tab styling
- [x] Test tab switching

**Files to Modify:**
- `src/pages/Review.tsx`

**UI Component:**
```typescript
const [questionTab, setQuestionTab] = useState<'both' | 'rubric' | 'feedback'>('both');

<div className="border-b border-slate-200">
  <nav className="flex space-x-8">
    <button
      onClick={() => setQuestionTab('both')}
      className={/* active/inactive styles */}
    >
      Both
    </button>
    <button
      onClick={() => setQuestionTab('rubric')}
      className={/* active/inactive styles */}
    >
      Grading Rubric
    </button>
    <button
      onClick={() => setQuestionTab('feedback')}
      className={/* active/inactive styles */}
    >
      Feedback
    </button>
  </nav>
</div>
```

### 10.2 Implement "Both" Tab View
- [x] Fetch rubric results from API
- [x] Display rubric response for each model pair
- [x] Display feedback and marks for each model pair
- [x] Show model pair names at top
- [x] Style rubric and feedback sections distinctly
- [x] Test with real data

**UI Structure:**
```typescript
{questionTab === 'both' && (
  <div className="space-y-6">
    {results.modelResults.map((modelResult) => (
      <div key={modelResult.model} className="bg-white rounded-xl p-6">
        <h4 className="font-bold text-lg mb-4">
          {modelResult.rubricModel} → {modelResult.assessmentModel}
        </h4>
        
        {modelResult.attempts.map((attempt) => (
          <div key={attempt.attemptNumber}>
            {/* Rubric Section */}
            <div className="bg-purple-50 rounded-lg p-4 mb-4">
              <h5 className="font-semibold mb-2">Grading Rubric Response:</h5>
              <p className="text-sm whitespace-pre-wrap">
                {attempt.rubricResponse}
              </p>
            </div>
            
            {/* Feedback Section */}
            <div className="bg-blue-50 rounded-lg p-4">
              <h5 className="font-semibold mb-2">Assessment Feedback:</h5>
              {/* Question feedback display */}
            </div>
          </div>
        ))}
      </div>
    ))}
  </div>
)}
```

### 10.3 Implement "Grading Rubric" Tab View
- [x] Display ONLY rubric responses
- [x] Show for each model and each attempt
- [x] Show model name
- [x] Add attempt numbering
- [x] Style for readability
- [x] Test with real data

### 10.4 Implement "Feedback" Tab View
- [x] Display ONLY feedback and marks
- [x] Show model pair names
- [x] Show for each attempt
- [x] Display marks prominently
- [x] Add visual hierarchy
- [x] Test with real data

### 10.5 Update Results Tab
- [x] Update table headers to show model pairs
- [x] Display as "Rubric Model → Assessment Model"
- [x] Ensure backward compatibility with old single-model results
- [x] Test display

---

## Phase 11: Frontend - Context/State Management
**Estimated Time:** 1 hour

### 11.1 Update AssessmentContext
- [x] Open `src/context/AssessmentContext.tsx`
- [x] Update `addAssessment()` to handle rubric images
- [x] Update `addAssessment()` to handle model pairs
- [x] Update image registration to include rubric role
- [x] Update session creation payload
- [x] Test context updates

**Files to Modify:**
- `src/context/AssessmentContext.tsx`

---

## Phase 12: Testing & Validation
**Estimated Time:** 2-3 hours

### 12.1 Backend Testing
- [ ] Test rubric prompt settings GET/PUT
- [ ] Test rubric image upload and registration
- [ ] Test single model pair grading
- [ ] Test multiple model pairs grading
- [ ] Test rubric LLM call with real API
- [ ] Test assessment LLM call with rubric text
- [ ] Test error handling (rubric fails, assessment succeeds)
- [ ] Test error handling (rubric succeeds, assessment fails)
- [ ] Test token usage tracking
- [ ] Verify database records
- [ ] Check session logs
- [ ] Test backward compatibility with old assessments

### 12.2 Frontend Testing
- [ ] Test rubric images upload
- [ ] Test model pair selection
- [ ] Test reasoning configuration for both models
- [ ] Test form validation
- [ ] Test assessment creation
- [ ] Test results page with rubric data
- [ ] Test all three sub-tabs
- [ ] Test backward compatibility (old assessments)
- [ ] Test error states
- [ ] Cross-browser testing

### 12.3 Integration Testing
- [ ] Test complete flow: create assessment → grade → view results
- [ ] Test with multiple iterations
- [ ] Test with different model combinations
- [ ] Test with missing rubric images (if optional)
- [ ] Test with very long rubric responses
- [ ] Performance testing with large datasets
- [ ] Test concurrent requests

---

## Phase 13: Documentation & Cleanup
**Estimated Time:** 1 hour

### 13.1 Code Documentation
- [ ] Add docstrings to new Python functions
- [ ] Add JSDoc comments to new TypeScript functions
- [ ] Update inline comments
- [ ] Document placeholder syntax

### 13.2 User Documentation
- [ ] Update README with grading rubric feature
- [ ] Create user guide for rubric setup
- [ ] Document model pairing concept
- [ ] Add screenshots of new UI
- [ ] Document new API endpoints

### 13.3 Code Cleanup
- [ ] Remove debug console.logs
- [ ] Remove commented code
- [ ] Format code consistently
- [ ] Run linter and fix issues
- [ ] Optimize imports

---

## Phase 14: Deployment Preparation
**Estimated Time:** 1 hour

### 14.1 Database Migration
- [ ] Test migration script on staging
- [ ] Create rollback script
- [ ] Document migration process
- [ ] Backup production database

### 14.2 Environment Configuration
- [ ] Update .env.example with any new variables
- [ ] Document new Supabase table requirements
- [ ] Update deployment scripts if needed

### 14.3 Final Checks
- [ ] All tests passing
- [ ] No TypeScript errors
- [ ] No console errors
- [ ] Performance benchmarks met
- [ ] Security review complete

---

## Progress Tracking

**Overall Progress:** 0% (0/87 tasks completed)

### Phase Completion Status
- [ ] Phase 1: Database Schema Changes (0/5)
- [ ] Phase 2: Backend - Schemas & Models (0/7)
- [ ] Phase 3: Backend - Settings Router (0/7)
- [ ] Phase 4: Backend - Grade Router (0/15)
- [ ] Phase 5: Backend - Results Router (0/5)
- [ ] Phase 6: Frontend - Type Definitions (0/7)
- [ ] Phase 7: Frontend - API Utils (0/8)
- [ ] Phase 8: Frontend - Settings Page (0/11)
- [ ] Phase 9: Frontend - NewAssessment Page (0/26)
- [ ] Phase 10: Frontend - Review Page (0/17)
- [ ] Phase 11: Frontend - Context/State Management (0/6)
- [ ] Phase 12: Testing & Validation (0/24)
- [ ] Phase 13: Documentation & Cleanup (0/10)
- [ ] Phase 14: Deployment Preparation (0/9)

---

## Notes & Decisions

### Design Decisions
- **Rubric Images:** Optional or Required? [Decision: ]
- **Rubric Failure Handling:** If rubric LLM fails, should assessment continue? [Decision: ]
- **Model Pairing UI:** How to visually indicate pairs? [Decision: ]
- **Backward Compatibility:** Keep old assessments working? [Decision: Yes]

### Known Issues
- [To be filled as issues arise]

### Future Enhancements
- [ ] Support multiple rubric models per assessment model
- [ ] Allow rubric reuse across assessments
- [ ] Add rubric templates library
- [ ] Add rubric quality scoring

---

## Team Notes
[Space for team members to add notes, blockers, or questions]

---

**Last Updated:** [Auto-update on each commit]
