# Grading Rubric Feature - Technical Specification

**Version:** 1.0  
**Last Updated:** [To be filled]  
**Status:** Draft

---

## Table of Contents
1. [Overview](#overview)
2. [Data Models](#data-models)
3. [API Endpoints](#api-endpoints)
4. [Database Schema](#database-schema)
5. [Frontend Components](#frontend-components)
6. [Data Flow](#data-flow)
7. [Error Handling](#error-handling)
8. [Backward Compatibility](#backward-compatibility)

---

## Overview

### Feature Summary
The grading rubric feature introduces a two-stage grading process:
1. **Stage 1 - Rubric Analysis:** A rubric model analyzes grading rubric images and extracts grading criteria
2. **Stage 2 - Assessment:** An assessment model grades student work using the extracted rubric

### Key Concepts
- **Model Pair:** A combination of (rubric_model, assessment_model)
- **Rubric Response:** Structured text output from the rubric model
- **Assessment Response:** Grading output from the assessment model using the rubric

---

## Data Models

### Backend Schemas

#### ModelPairSpec
```python
class ModelPairSpec(BaseModel):
    rubric_model: ModelSpec      # Model for rubric analysis
    assessment_model: ModelSpec  # Model for actual grading
    instance_id: str | None = None  # Unique identifier for this pair
```

#### ModelSpec (Extended)
```python
class ModelSpec(BaseModel):
    name: str                    # Model ID (e.g., "anthropic/claude-3.5-sonnet")
    tries: int | None = None     # Number of attempts
    reasoning: Dict[str, Any] | None = None  # Reasoning configuration
    instance_id: str | None = None  # Instance identifier
```

#### GradeSingleReq (Updated)
```python
class GradeSingleReq(BaseModel):
    session_id: str
    model_pairs: List[ModelPairSpec] | None = None  # NEW: Model pairs
    models: List[ModelSpec] | None = None  # LEGACY: Single models
    default_tries: int | None = 1
    reasoning: Dict[str, Any] | None = None  # Global reasoning (legacy)
```

#### RubricPromptSettingsReq
```python
class RubricPromptSettingsReq(BaseModel):
    system_template: str  # System prompt for rubric analysis
    user_template: str    # User prompt for rubric analysis
```

#### RubricPromptSettingsRes
```python
class RubricPromptSettingsRes(BaseModel):
    system_template: str
    user_template: str
```

### Frontend Types

#### ModelPair
```typescript
interface ModelPair {
  rubricModel: string;              // Model ID for rubric
  assessmentModel: string;          // Model ID for assessment
  rubricReasoning?: ReasoningConfig;   // Reasoning config for rubric
  assessmentReasoning?: ReasoningConfig; // Reasoning config for assessment
  instanceId?: string;              // Unique pair identifier
}
```

#### Assessment (Updated)
```typescript
interface Assessment {
  id: string;
  name: string;
  date: string;
  status: 'running' | 'complete' | 'failed';
  
  // Images
  studentImages: File[];
  answerKeyImages: File[];
  rubricImages: File[];  // NEW
  
  // Configuration
  questions: string;
  humanGrades: string;
  iterations: number;
  
  // Models - NEW approach
  modelPairs: ModelPair[];  // NEW: For new assessments
  
  // Models - LEGACY approach (keep for backward compat)
  selectedModels: string[];
  reasoningBySelection?: ReasoningConfig[];
  
  // Results
  results?: AssessmentResults;
}
```

#### ModelResult (Updated)
```typescript
interface ModelResult {
  // NEW fields
  rubricModel?: string;      // Rubric model ID
  assessmentModel?: string;  // Assessment model ID
  
  // LEGACY field (keep for backward compat)
  model: string;  // Combined or single model ID
  
  averages: {
    discrepancies100: number;
    questionDiscrepancies100: number;
    zpfDiscrepancies: number;
    zpfQuestionDiscrepancies: number;
    rangeDiscrepancies: number;
    rangeQuestionDiscrepancies: number;
    totalScore: number;
  };
  attempts: Attempt[];
}
```

#### Attempt (Updated)
```typescript
interface Attempt {
  attemptNumber: number;
  
  // NEW field
  rubricResponse?: string;  // Rubric analysis output
  
  // Existing fields
  discrepancies100: number;
  questionDiscrepancies100: number;
  zpfDiscrepancies: number;
  zpfQuestionDiscrepancies: number;
  rangeDiscrepancies: number;
  rangeQuestionDiscrepancies: number;
  totalScore: number;
  questionFeedback: QuestionFeedback[];
  lt100Questions?: string[];
  zpfQuestions?: string[];
  rangeQuestions?: string[];
  failureReasons?: string[];
  tokenUsage?: TokenUsage;
}
```

---

## API Endpoints

### Rubric Prompt Settings

#### GET /settings/rubric-prompt
Retrieve rubric prompt templates.

**Response:** 200 OK
```json
{
  "system_template": "You are a grading rubric analyzer...",
  "user_template": "Please analyze the grading rubric..."
}
```

#### PUT /settings/rubric-prompt
Update rubric prompt templates.

**Request Body:**
```json
{
  "system_template": "string",
  "user_template": "string"
}
```

**Response:** 200 OK
```json
{
  "system_template": "string",
  "user_template": "string"
}
```

### Rubric Results

#### GET /results/{session_id}/rubric
Retrieve rubric analysis results for a session.

**Response:** 200 OK
```json
{
  "session_id": "uuid",
  "rubric_results": {
    "model_name": {
      "1": {  // try_index
        "rubric_response": "Extracted rubric text...",
        "raw_output": {},
        "validation_errors": null
      }
    }
  }
}
```

### Image Registration (Updated)

#### POST /images/register
Register an image with the session.

**Request Body:**
```json
{
  "session_id": "uuid",
  "role": "student" | "answer_key" | "grading_rubric",  // NEW: grading_rubric
  "url": "string",
  "order_index": 0
}
```

### Grade Single (Updated)

#### POST /grade/single
Start grading process with model pairs.

**Request Body (New Format):**
```json
{
  "session_id": "uuid",
  "model_pairs": [
    {
      "rubric_model": {
        "name": "anthropic/claude-3.5-sonnet",
        "tries": 3,
        "reasoning": { "level": "medium" }
      },
      "assessment_model": {
        "name": "openai/gpt-4",
        "tries": 3,
        "reasoning": null
      },
      "instance_id": "pair_0"
    }
  ],
  "default_tries": 3
}
```

**Request Body (Legacy Format - Still Supported):**
```json
{
  "session_id": "uuid",
  "models": [
    {
      "name": "anthropic/claude-3.5-sonnet",
      "tries": 3,
      "reasoning": null
    }
  ],
  "default_tries": 3
}
```

---

## Database Schema

### New Table: rubric_result

```sql
CREATE TABLE rubric_result (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES session(id) ON DELETE CASCADE,
  model_name TEXT NOT NULL,           -- Rubric model identifier
  try_index INTEGER NOT NULL,         -- Attempt number
  rubric_response TEXT,               -- Extracted rubric text
  raw_output JSONB,                   -- Full OpenRouter response
  validation_errors JSONB,            -- Errors if parsing failed
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  
  CONSTRAINT unique_rubric_per_attempt 
    UNIQUE (session_id, model_name, try_index)
);

CREATE INDEX idx_rubric_result_session ON rubric_result(session_id);
CREATE INDEX idx_rubric_result_model_try ON rubric_result(model_name, try_index);
```

### Updated Table: image

```sql
-- Update role constraint to include 'grading_rubric'
ALTER TABLE image DROP CONSTRAINT IF EXISTS image_role_check;
ALTER TABLE image ADD CONSTRAINT image_role_check 
  CHECK (role IN ('student', 'answer_key', 'grading_rubric'));
```

### Updated Table: session

```sql
-- Add columns to track model pair configuration
ALTER TABLE session 
  ADD COLUMN IF NOT EXISTS rubric_model TEXT,
  ADD COLUMN IF NOT EXISTS assessment_model TEXT;
```

### App Settings Entry

```sql
-- Rubric prompt settings stored in app_settings table
-- key: 'rubric_prompt_settings'
-- value: JSONB with structure:
{
  "system_template": "string",
  "user_template": "string"
}
```

---

## Frontend Components

### Settings Page - New Tab

**Component:** Rubric Prompt Settings Tab  
**Location:** `src/pages/Settings.tsx`

**Features:**
- System template textarea
- User template textarea
- Save/Reset buttons
- Real-time validation
- Preview placeholders

**Placeholders Supported:**
- `[Grading rubric images]` - Replaced with rubric image URLs
- `[Question list]` - Replaced with JSON question list

### NewAssessment Page - Dual Model Selectors

**Component:** Model Pair Selection  
**Location:** `src/pages/NewAssessment.tsx`

**UI Layout:**
```
┌─────────────────────────────────────────┐
│  Grading Rubric Models                  │
│  [Model Selector 1]                     │
│  Selected: Claude 3.5 Sonnet            │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Assessment Models (pairs with above)   │
│  [Model Selector 2]                     │
│  Selected: GPT-4                        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Model Pairs Preview                    │
│  Pair 1: Claude 3.5 Sonnet → GPT-4     │
│  Pair 2: GPT-4 → Claude 3.5 Sonnet     │
└─────────────────────────────────────────┘
```

**Features:**
- Synchronized pair selection (indices match)
- Individual reasoning config per model
- Visual pair indicators
- Validation: Must have equal counts

### NewAssessment Page - Rubric Images Upload

**Component:** Rubric Images Upload  
**Location:** `src/pages/NewAssessment.tsx`

**Features:**
- File upload via FileUpload component
- Multiple image support
- Preview thumbnails
- Drag-and-drop support
- Validation indicators

### Review Page - Sub-Tabs

**Component:** Question Analysis Sub-Tabs  
**Location:** `src/pages/Review.tsx`

**Tab Structure:**
```
┌─────────────────────────────────────────┐
│  [Both] [Grading Rubric] [Feedback]     │
└─────────────────────────────────────────┘
```

#### Both Tab
Shows rubric response AND assessment feedback for each model pair and attempt.

**Layout:**
```
Model Pair: Claude 3.5 Sonnet → GPT-4

Attempt 1:
  ┌─────────────────────────────────────┐
  │ Grading Rubric Response             │
  │ [Rubric text from rubric model]     │
  └─────────────────────────────────────┘
  
  ┌─────────────────────────────────────┐
  │ Assessment Feedback                 │
  │ Q1: 8/10 - Good answer...           │
  │ Q2: 6/10 - Missing key points...    │
  └─────────────────────────────────────┘
```

#### Grading Rubric Tab
Shows ONLY rubric responses for all models and attempts.

#### Feedback Tab
Shows ONLY assessment feedback and marks for all model pairs and attempts.

---

## Data Flow

### Assessment Creation Flow

```
1. User fills form in NewAssessment page
   ├─ Selects rubric models
   ├─ Selects assessment models (creates pairs)
   ├─ Uploads rubric images
   ├─ Uploads student images
   └─ Uploads answer key images (optional)

2. Submit button clicked
   ├─ Create session via POST /sessions
   ├─ Upload rubric images to Supabase
   ├─ Register rubric images via POST /images/register (role: grading_rubric)
   ├─ Upload student images to Supabase
   ├─ Register student images via POST /images/register (role: student)
   ├─ Upload answer key images to Supabase (if provided)
   ├─ Register answer key images via POST /images/register (role: answer_key)
   ├─ Configure questions via POST /questions/config
   └─ Start grading via POST /grade/single with model_pairs

3. Backend processes model pairs
   For each (rubric_model, assessment_model, try_index):
     ├─ Load rubric images from database
     ├─ Build rubric messages with templates
     ├─ Call rubric LLM (_call_rubric_llm)
     │  ├─ POST to OpenRouter with rubric model
     │  ├─ Parse rubric response
     │  └─ Store in rubric_result table
     ├─ Build assessment messages with templates
     │  └─ Include rubric response in messages
     ├─ Call assessment LLM (_call_openrouter)
     │  ├─ POST to OpenRouter with assessment model
     │  └─ Parse assessment response
     └─ Store results in result table

4. User views results in Review page
   ├─ Fetch results via GET /results/{session_id}
   ├─ Fetch rubric results via GET /results/{session_id}/rubric
   └─ Display in sub-tabs (Both, Rubric, Feedback)
```

### Rubric Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Rubric Processing                        │
└─────────────────────────────────────────────────────────────┘

1. Load rubric prompt templates from Supabase
   └─ GET app_settings WHERE key = 'rubric_prompt_settings'

2. Build rubric messages
   ├─ System message with placeholders:
   │  └─ [Grading rubric images] → Array of image URLs
   │  └─ [Question list] → JSON of questions
   └─ User message with instructions

3. Call OpenRouter API
   ├─ Model: rubric_model from pair
   ├─ Messages: Built in step 2
   └─ Reasoning: From rubric_model.reasoning config

4. Parse rubric response
   ├─ Extract text from OpenRouter response
   └─ Store in rubric_result table

5. Return rubric text
   └─ Used as input for assessment model
```

### Assessment Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   Assessment Processing                      │
└─────────────────────────────────────────────────────────────┘

1. Load assessment prompt templates from Supabase
   └─ GET app_settings WHERE key = 'prompt_settings'

2. Build assessment messages
   ├─ System message with placeholders:
   │  ├─ [Answer key] → Array of answer key image URLs
   │  ├─ [Question list] → JSON of questions
   │  ├─ [Response schema] → Expected JSON structure
   │  └─ [Grading Rubric] → Rubric text from rubric model (NEW)
   └─ User message with placeholders:
      └─ [Student assessment] → Array of student image URLs

3. Call OpenRouter API
   ├─ Model: assessment_model from pair
   ├─ Messages: Built in step 2
   └─ Reasoning: From assessment_model.reasoning config

4. Parse assessment response
   ├─ Extract JSON with grades
   ├─ Validate structure
   └─ Store in result table

5. Return results
   └─ Used for statistics and display
```

---

## Error Handling

### Rubric LLM Failures

**Scenario:** Rubric model fails to respond or returns invalid format

**Handling:**
1. Log error with details
2. Store error in `rubric_result.validation_errors`
3. Decision point:
   - **Option A:** Continue with assessment using empty/default rubric
   - **Option B:** Fail the entire pair attempt
   - **Recommended:** Option B - Fail the pair attempt

**Frontend Display:**
- Show error badge in results
- Display error message in "Both" and "Rubric" tabs
- Assessment feedback section shows "N/A - Rubric failed"

### Assessment LLM Failures

**Scenario:** Assessment model fails after rubric succeeded

**Handling:**
1. Log error with details
2. Store error in `result.validation_errors`
3. Mark attempt as failed but keep rubric result
4. Continue with other attempts

**Frontend Display:**
- Show rubric response (succeeded)
- Show error message for assessment feedback
- Mark attempt as failed in results table

### Image Upload Failures

**Scenario:** Rubric image upload fails

**Handling:**
1. Show error in NewAssessment page
2. Prevent form submission
3. Allow retry

### Template Loading Failures

**Scenario:** Cannot load rubric prompt templates from database

**Handling:**
1. Fall back to DEFAULT_RUBRIC_SYSTEM_TEMPLATE
2. Fall back to DEFAULT_RUBRIC_USER_TEMPLATE
3. Log warning
4. Continue processing

---

## Backward Compatibility

### Supporting Old Assessments

**Challenge:** Existing assessments use single models, not pairs

**Solution:**

#### Database
- Keep `selectedModels` field in session table
- New assessments populate `rubric_model` and `assessment_model`
- Old assessments leave these NULL

#### API
- `grade_single` endpoint accepts BOTH:
  - `model_pairs` (new format)
  - `models` (legacy format)
- If `models` provided, use legacy flow (no rubric)
- If `model_pairs` provided, use new flow (with rubric)

#### Frontend
- Assessment type stores both `modelPairs` and `selectedModels`
- Check which field is populated to determine display logic
- Review page checks for `rubricModel` and `assessmentModel`
  - If present: Show model pairs and sub-tabs
  - If absent: Show single model (legacy display)

### Migration Strategy

**No database migration needed for existing data**

Old assessments continue to work exactly as before. New assessments use the new rubric functionality.

**Display Logic:**
```typescript
// In Review.tsx
const isLegacyAssessment = !modelResult.rubricModel && !modelResult.assessmentModel;

if (isLegacyAssessment) {
  // Use old display logic (single model)
  return <LegacyView />;
} else {
  // Use new display logic (model pairs with sub-tabs)
  return <NewViewWithSubTabs />;
}
```

---

## Placeholder Syntax

### Rubric Prompts

**Supported Placeholders:**
- `[Grading rubric images]` - Replaced with image_url objects
- `[Question list]` - Replaced with JSON question array

**Example:**
```
System Template:
You are a grading rubric analyzer.

Here are the rubric images:
[Grading rubric images]

Here are the questions to grade:
[Question list]

Please extract the grading criteria.
```

**After Replacement:**
```
System Template:
You are a grading rubric analyzer.

Here are the rubric images:
[image_url: https://supabase.../rubric1.jpg]
[image_url: https://supabase.../rubric2.jpg]

Here are the questions to grade:
{
  "question_list": [
    {"question_number": "Q1", "max_mark": 10},
    {"question_number": "Q2", "max_mark": 15}
  ]
}

Please extract the grading criteria.
```

### Assessment Prompts

**Supported Placeholders:**
- `[Answer key]` - Replaced with image_url objects
- `[Question list]` - Replaced with JSON question array
- `[Response schema]` - Replaced with schema template
- `[Student assessment]` - Replaced with image_url objects
- `[Grading Rubric]` - **NEW** - Replaced with rubric text from rubric model

**Example:**
```
System Template:
You are a grader.

Answer key:
[Answer key]

Grading rubric extracted:
[Grading Rubric]

Questions:
[Question list]

Expected output:
[Response schema]
```

---

## Security Considerations

### Image Upload
- Validate file types (images only)
- Validate file sizes (max 10MB per image)
- Sanitize filenames
- Use secure Supabase storage URLs

### API Keys
- Store OpenRouter API key in environment variables
- Never expose in frontend code
- Rotate keys periodically

### Database
- Use prepared statements (already done via Supabase client)
- Validate UUIDs for session_id
- Proper foreign key constraints

### Templates
- Sanitize user input in templates
- Prevent injection attacks
- Validate template structure before saving

---

## Performance Considerations

### Concurrent Requests
- Limit concurrent rubric LLM calls via semaphore
- Limit concurrent assessment LLM calls via semaphore
- Current limit: 4 concurrent requests (configurable)

### Token Usage
- Track tokens for BOTH rubric and assessment calls
- Store separately in `token_usage` table
- Display in UI (hover tooltip)

### Database Queries
- Use indexes on `session_id`, `model_name`, `try_index`
- Batch upserts (50 records per batch)
- Connection pooling via Supabase

### Large Rubric Responses
- Consider truncating very long rubric responses (>10,000 chars)
- Add warning in UI if truncated
- Store full response in `raw_output` JSONB field

---

## Testing Strategy

### Unit Tests
- [ ] Test `_build_rubric_messages()` with various inputs
- [ ] Test `_call_rubric_llm()` with mock responses
- [ ] Test `_build_messages()` with rubric text
- [ ] Test placeholder replacement logic
- [ ] Test error handling functions

### Integration Tests
- [ ] Test complete flow: rubric → assessment
- [ ] Test with actual OpenRouter API
- [ ] Test with multiple model pairs
- [ ] Test backward compatibility with old assessments
- [ ] Test error scenarios (rubric fails, assessment fails)

### Frontend Tests
- [ ] Test model pair selection logic
- [ ] Test sub-tab navigation
- [ ] Test data display in all tabs
- [ ] Test form validation
- [ ] Test backward compatibility display

### Performance Tests
- [ ] Test with 10+ model pairs
- [ ] Test with 100+ questions
- [ ] Test with large rubric images (5MB+)
- [ ] Test concurrent grading sessions

---

## Deployment Checklist

- [ ] Database migration tested on staging
- [ ] Environment variables configured
- [ ] OpenRouter API tested in production
- [ ] Supabase storage bucket configured
- [ ] Default templates populated in database
- [ ] Frontend build successful
- [ ] Backend tests passing
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Team training completed

---

**Document Version History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | [Date] | [Name] | Initial specification |

