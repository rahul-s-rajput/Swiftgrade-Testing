# Grading Rubric Feature - Architecture & Flow Diagrams

**Visual reference for understanding the grading rubric feature architecture**

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Frontend (React + TypeScript)             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │   Settings   │  │ NewAssessment│  │    Review    │            │
│  │              │  │              │  │              │            │
│  │  - LLM       │  │  - 2x Model  │  │  - Results   │            │
│  │    Prompts   │  │    Selectors │  │  - Sub-tabs  │            │
│  │  - Rubric    │  │  - Rubric    │  │    • Both    │            │
│  │    Prompts   │  │    Images    │  │    • Rubric  │            │
│  └──────────────┘  └──────────────┘  │    • Feedback│            │
│                                       └──────────────┘            │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │            AssessmentContext (State Management)              │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ REST API
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI + Python)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │   Settings   │  │    Grade     │  │   Results    │            │
│  │    Router    │  │    Router    │  │    Router    │            │
│  │              │  │              │  │              │            │
│  │  - Prompts   │  │  - Rubric    │  │  - Grading   │            │
│  │    GET/PUT   │  │    LLM       │  │    Results   │            │
│  │  - Rubric    │  │  - Assessment│  │  - Rubric    │            │
│  │    Prompts   │  │    LLM       │  │    Results   │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                    │                            │
                    │                            │
                    ▼                            ▼
┌────────────────────────────┐   ┌──────────────────────────────────┐
│   Supabase (PostgreSQL)    │   │    OpenRouter API (LLMs)         │
├────────────────────────────┤   ├──────────────────────────────────┤
│                            │   │                                  │
│  • session                 │   │  Rubric Models:                  │
│  • image (3 roles)         │   │  • Claude 3.5 Sonnet            │
│  • question                │   │  • GPT-4                        │
│  • result                  │   │  • Gemini                       │
│  • rubric_result (NEW)     │   │  • etc.                         │
│  • app_settings            │   │                                  │
│  • token_usage             │   │  Assessment Models:              │
│                            │   │  • Claude 3.5 Sonnet            │
│  Supabase Storage:         │   │  • GPT-4                        │
│  • student images          │   │  • Gemini                       │
│  • answer key images       │   │  • etc.                         │
│  • rubric images (NEW)     │   │                                  │
└────────────────────────────┘   └──────────────────────────────────┘
```

---

## Data Flow: Assessment Creation

```
┌──────────────┐
│     User     │
└──────┬───────┘
       │
       │ 1. Fill form
       ▼
┌──────────────────────────────────────┐
│   NewAssessment Page (Frontend)      │
│                                      │
│  • Select Rubric Model(s)            │
│  • Select Assessment Model(s)        │
│  • Upload Rubric Images              │
│  • Upload Student Images             │
│  • Upload Answer Key Images          │
│  • Configure Questions               │
└──────┬───────────────────────────────┘
       │
       │ 2. Submit
       ▼
┌──────────────────────────────────────┐
│   AssessmentContext                  │
│   addAssessment()                    │
└──────┬───────────────────────────────┘
       │
       │ 3. Create session
       ▼
┌──────────────────────────────────────┐
│   POST /sessions                     │
│   Response: { session_id }           │
└──────┬───────────────────────────────┘
       │
       │ 4. Upload images
       ▼
┌──────────────────────────────────────┐
│   For each image:                    │
│   1. GET /images/signed-url          │
│   2. PUT to Supabase Storage         │
│   3. POST /images/register           │
│      role: "grading_rubric" (NEW)    │
│      role: "student"                 │
│      role: "answer_key"              │
└──────┬───────────────────────────────┘
       │
       │ 5. Configure questions
       ▼
┌──────────────────────────────────────┐
│   POST /questions/config             │
└──────┬───────────────────────────────┘
       │
       │ 6. Start grading
       ▼
┌──────────────────────────────────────┐
│   POST /grade/single                 │
│   {                                  │
│     session_id: "...",               │
│     model_pairs: [                   │
│       {                              │
│         rubric_model: {...},         │
│         assessment_model: {...}      │
│       }                              │
│     ]                                │
│   }                                  │
└──────┬───────────────────────────────┘
       │
       │ 7. Process in background
       ▼
    (See Grading Flow below)
```

---

## Data Flow: Grading Process (Per Model Pair)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    grade_single() - Backend                         │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ For each model pair
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       STAGE 1: Rubric Analysis                      │
└─────────────────────────────────────────────────────────────────────┘
       │
       │ 1. Load rubric images from DB
       ▼
┌──────────────────────────────────────┐
│   SELECT * FROM image                │
│   WHERE role = 'grading_rubric'      │
└──────┬───────────────────────────────┘
       │
       │ 2. Load rubric prompt templates
       ▼
┌──────────────────────────────────────┐
│   SELECT * FROM app_settings         │
│   WHERE key = 'rubric_prompt...'     │
└──────┬───────────────────────────────┘
       │
       │ 3. Build rubric messages
       ▼
┌──────────────────────────────────────┐
│   _build_rubric_messages()           │
│                                      │
│   System:                            │
│   "You are a rubric analyzer..."     │
│   [Grading rubric images]            │
│   [Question list]                    │
│                                      │
│   User:                              │
│   "Extract grading criteria..."      │
└──────┬───────────────────────────────┘
       │
       │ 4. Call rubric LLM
       ▼
┌──────────────────────────────────────┐
│   _call_rubric_llm()                 │
│                                      │
│   POST to OpenRouter:                │
│   {                                  │
│     model: "rubric_model",           │
│     messages: [...],                 │
│     reasoning: {...}                 │
│   }                                  │
└──────┬───────────────────────────────┘
       │
       │ 5. Parse & store rubric response
       ▼
┌──────────────────────────────────────┐
│   Extract rubric text from response  │
│                                      │
│   INSERT INTO rubric_result          │
│   {                                  │
│     session_id,                      │
│     model_name: "rubric_model",      │
│     try_index,                       │
│     rubric_response: "...",          │
│     raw_output: {...}                │
│   }                                  │
└──────┬───────────────────────────────┘
       │
       │ rubric_text = "Extracted criteria..."
       │
       │
┌─────────────────────────────────────────────────────────────────────┐
│                   STAGE 2: Assessment with Rubric                   │
└─────────────────────────────────────────────────────────────────────┘
       │
       │ 6. Load student & answer key images
       ▼
┌──────────────────────────────────────┐
│   SELECT * FROM image                │
│   WHERE role IN                      │
│     ('student', 'answer_key')        │
└──────┬───────────────────────────────┘
       │
       │ 7. Load assessment prompt templates
       ▼
┌──────────────────────────────────────┐
│   SELECT * FROM app_settings         │
│   WHERE key = 'prompt_settings'      │
└──────┬───────────────────────────────┘
       │
       │ 8. Build assessment messages
       ▼
┌──────────────────────────────────────┐
│   _build_messages(                   │
│     ...,                             │
│     rubric_text = rubric_text        │
│   )                                  │
│                                      │
│   System:                            │
│   "You are a grader..."              │
│   [Answer key]                       │
│   [Question list]                    │
│   [Response schema]                  │
│   [Grading Rubric] ← NEW!            │
│   "Use this rubric: {rubric_text}"   │
│                                      │
│   User:                              │
│   "Grade this student work..."       │
│   [Student assessment]               │
└──────┬───────────────────────────────┘
       │
       │ 9. Call assessment LLM
       ▼
┌──────────────────────────────────────┐
│   _call_openrouter()                 │
│                                      │
│   POST to OpenRouter:                │
│   {                                  │
│     model: "assessment_model",       │
│     messages: [...],                 │
│     reasoning: {...}                 │
│   }                                  │
└──────┬───────────────────────────────┘
       │
       │ 10. Parse & store assessment results
       ▼
┌──────────────────────────────────────┐
│   Extract grades from response       │
│                                      │
│   INSERT INTO result                 │
│   {                                  │
│     session_id,                      │
│     question_id,                     │
│     model_name: "pair_instance_id",  │
│     try_index,                       │
│     marks_awarded,                   │
│     rubric_notes,                    │
│     raw_output: {...}                │
│   }                                  │
└──────┬───────────────────────────────┘
       │
       │ 11. Update session status
       ▼
┌──────────────────────────────────────┐
│   UPDATE session                     │
│   SET status = 'graded'              │
│   WHERE id = session_id              │
└──────────────────────────────────────┘
```

---

## Data Flow: Viewing Results

```
┌──────────────┐
│     User     │
└──────┬───────┘
       │
       │ Navigate to Review page
       ▼
┌─────────────────────────────────────────┐
│   Review Page (Frontend)                │
└──────┬──────────────────────────────────┘
       │
       │ 1. Load assessment results
       ▼
┌─────────────────────────────────────────┐
│   GET /results/{session_id}             │
│   Response:                             │
│   {                                     │
│     modelResults: [                     │
│       {                                 │
│         rubricModel: "...",             │
│         assessmentModel: "...",         │
│         attempts: [                     │
│           {                             │
│             attemptNumber: 1,           │
│             questionFeedback: [...]     │
│           }                             │
│         ]                               │
│       }                                 │
│     ]                                   │
│   }                                     │
└──────┬──────────────────────────────────┘
       │
       │ 2. Load rubric results
       ▼
┌─────────────────────────────────────────┐
│   GET /results/{session_id}/rubric      │
│   Response:                             │
│   {                                     │
│     rubric_results: {                   │
│       "model_name": {                   │
│         "1": {                          │
│           rubric_response: "...",       │
│           raw_output: {...}             │
│         }                               │
│       }                                 │
│     }                                   │
│   }                                     │
└──────┬──────────────────────────────────┘
       │
       │ 3. Merge data
       ▼
┌─────────────────────────────────────────┐
│   Combine rubric results with           │
│   assessment results                    │
│                                         │
│   For each attempt:                     │
│     attempt.rubricResponse =            │
│       rubric_results[model][try]        │
└──────┬──────────────────────────────────┘
       │
       │ 4. Display in UI
       ▼
┌─────────────────────────────────────────┐
│   Sub-tabs:                             │
│                                         │
│   [Both Tab]                            │
│   • Rubric Response (purple box)        │
│   • Assessment Feedback (blue box)      │
│                                         │
│   [Grading Rubric Tab]                  │
│   • Only Rubric Response                │
│                                         │
│   [Feedback Tab]                        │
│   • Only Assessment Feedback            │
└─────────────────────────────────────────┘
```

---

## Database Schema Relationships

```
┌─────────────────────────┐
│       session           │
│─────────────────────────│
│ id (PK)                 │
│ name                    │
│ status                  │
│ created_at              │
│ selected_models         │
│ rubric_model (NEW)      │
│ assessment_model (NEW)  │
└────────┬────────────────┘
         │
         │ 1:N
         │
    ┌────┴────┬───────┬────────┐
    │         │       │        │
    ▼         ▼       ▼        ▼
┌─────────┐ ┌────────┐ ┌──────────────┐ ┌──────────────┐
│  image  │ │question│ │   result     │ │rubric_result │
│─────────│ │────────│ │──────────────│ │──────────────│
│ id (PK) │ │ id (PK)│ │ id (PK)      │ │ id (PK)      │
│ session │ │ session│ │ session_id   │ │ session_id   │
│ role    │ │ q_id   │ │ question_id  │ │ model_name   │
│ • stud. │ │ number │ │ model_name   │ │ try_index    │
│ • key   │ │ max_m. │ │ try_index    │ │ rubric_resp. │
│ • rubric│ │        │ │ marks        │ │ raw_output   │
│ url     │ │        │ │ rubric_notes │ │ val_errors   │
│ order   │ │        │ │ raw_output   │ └──────────────┘
└─────────┘ └────────┘ │ val_errors   │
                       └──────────────┘

                       ┌──────────────┐
                       │ token_usage  │
                       │──────────────│
                       │ id (PK)      │
                       │ session_id   │
                       │ model_name   │
                       │ try_index    │
                       │ input_tokens │
                       │ output_token │
                       │ reasoning_t. │
                       │ total_tokens │
                       └──────────────┘

┌─────────────────────────┐
│     app_settings        │
│─────────────────────────│
│ key (PK)                │
│ • 'prompt_settings'     │
│ • 'rubric_prompt...'    │
│ value (JSONB)           │
│ updated_at              │
└─────────────────────────┘
```

---

## Component Hierarchy

```
src/
│
├── pages/
│   │
│   ├── Settings.tsx
│   │   ├── Tab: LLM Prompts
│   │   │   ├── System Template Textarea
│   │   │   ├── User Template Textarea
│   │   │   └── Schema Template Textarea
│   │   │
│   │   └── Tab: Rubric Prompts (NEW)
│   │       ├── System Template Textarea
│   │       └── User Template Textarea
│   │
│   ├── NewAssessment.tsx
│   │   ├── Test Name Input
│   │   ├── Rubric Images Upload (NEW)
│   │   ├── Student Images Upload
│   │   ├── Answer Key Images Upload
│   │   ├── Questions JSON Textarea
│   │   ├── Human Grades JSON Textarea
│   │   │
│   │   ├── Rubric Model Selector (NEW)
│   │   │   ├── MultiSelect Component
│   │   │   ├── Reasoning Config Menu
│   │   │   └── Model Chips
│   │   │
│   │   ├── Assessment Model Selector (NEW)
│   │   │   ├── MultiSelect Component
│   │   │   ├── Reasoning Config Menu
│   │   │   └── Model Chips
│   │   │
│   │   ├── Model Pairs Preview (NEW)
│   │   │   └── List of pairs with → arrow
│   │   │
│   │   ├── Iterations Number Input
│   │   └── Submit Button
│   │
│   └── Review.tsx
│       ├── Performance Results Tab
│       │   └── Results Table
│       │       ├── Model Pair Names
│       │       ├── Average Rows
│       │       └── Attempt Rows
│       │
│       └── Question Analysis Tab
│           ├── Question Navigator
│           ├── Human Grade Display
│           │
│           └── Sub-tabs (NEW)
│               ├── Both Tab
│               │   └── For each model pair:
│               │       └── For each attempt:
│               │           ├── Rubric Response Section
│               │           └── Feedback Section
│               │
│               ├── Grading Rubric Tab
│               │   └── For each model:
│               │       └── For each attempt:
│               │           └── Rubric Response Only
│               │
│               └── Feedback Tab
│                   └── For each model pair:
│                       └── For each attempt:
│                           └── Feedback Only
│
├── context/
│   └── AssessmentContext.tsx
│       ├── addAssessment()
│       │   ├── Upload rubric images (NEW)
│       │   ├── Upload student images
│       │   ├── Upload answer key images
│       │   ├── Register all images
│       │   └── Start grading with model_pairs
│       │
│       ├── loadAssessmentResults()
│       └── getAssessment()
│
└── utils/
    └── api.ts
        ├── getRubricPromptSettings() (NEW)
        ├── putRubricPromptSettings() (NEW)
        ├── getRubricResults() (NEW)
        ├── gradeSingleWithRetry() (UPDATED)
        └── registerImage() (UPDATED)
```

---

## Message Flow: Rubric Analysis

```
Frontend Request:
POST /grade/single
{
  model_pairs: [
    {
      rubric_model: {
        name: "anthropic/claude-3.5-sonnet",
        reasoning: { level: "medium" }
      },
      assessment_model: { ... }
    }
  ]
}
         │
         ▼
Backend Processing:
_build_rubric_messages(rubric_urls, questions)
         │
         ▼
Messages to OpenRouter:
[
  {
    role: "system",
    content: "You are a rubric analyzer...\n\n
              Rubric images: [image_urls]\n
              Questions: {json}\n
              Extract criteria..."
  },
  {
    role: "user",
    content: "Please analyze the grading rubric..."
  }
]
         │
         ▼
OpenRouter API:
POST https://openrouter.ai/api/v1/chat/completions
{
  model: "anthropic/claude-3.5-sonnet",
  messages: [...],
  reasoning: { effort: "medium" }
}
         │
         ▼
OpenRouter Response:
{
  choices: [{
    message: {
      content: "Based on the rubric images:
                Q1 (10 marks): Award full marks for...
                Q2 (15 marks): Deduct 2 marks if..."
    }
  }],
  usage: {
    prompt_tokens: 1200,
    completion_tokens: 450,
    reasoning_tokens: 300
  }
}
         │
         ▼
Backend Storage:
INSERT INTO rubric_result
{
  session_id: "...",
  model_name: "anthropic/claude-3.5-sonnet",
  try_index: 1,
  rubric_response: "Based on the rubric images...",
  raw_output: { ... }
}
         │
         ▼
Return rubric_text for assessment stage
```

---

## Message Flow: Assessment with Rubric

```
Backend Processing:
_build_messages(
  student_urls,
  key_urls,
  questions,
  rubric_text = "Based on the rubric images..."  ← From Stage 1
)
         │
         ▼
Messages to OpenRouter:
[
  {
    role: "system",
    content: "You are a grader...\n\n
              Answer key: [image_urls]\n
              Questions: {json}\n
              Response schema: {...}\n\n
              GRADING RUBRIC:\n
              Based on the rubric images...\n  ← Injected here!
              Q1 (10 marks): Award full marks for...\n
              Q2 (15 marks): Deduct 2 marks if...\n\n
              Use this rubric to grade."
  },
  {
    role: "user",
    content: "Grade this student work:\n
              [student_image_urls]"
  }
]
         │
         ▼
OpenRouter API:
POST https://openrouter.ai/api/v1/chat/completions
{
  model: "openai/gpt-4",
  messages: [...],
  reasoning: null
}
         │
         ▼
OpenRouter Response:
{
  choices: [{
    message: {
      content: '{
        "result": [{
          "first_name": "John",
          "last_name": "Doe",
          "answers": [
            {
              "question_id": "Q1",
              "marks_awarded": 8,
              "rubric_notes": "Good answer, minor error..."
            }
          ]
        }]
      }'
    }
  }]
}
         │
         ▼
Backend Storage:
INSERT INTO result
{
  session_id: "...",
  question_id: "Q1",
  model_name: "pair_instance_id",
  try_index: 1,
  marks_awarded: 8,
  rubric_notes: "Good answer, minor error...",
  raw_output: { ... }
}
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────┐
│   Rubric LLM Call                       │
└──────┬──────────────────────────────────┘
       │
       ├─ SUCCESS ──────────┐
       │                    │
       │                    ▼
       │         ┌──────────────────────────┐
       │         │ rubric_text = "..."      │
       │         │ Store in rubric_result   │
       │         └──────┬───────────────────┘
       │                │
       │                ▼
       │         ┌──────────────────────────┐
       │         │ Assessment LLM Call      │
       │         └──────┬───────────────────┘
       │                │
       │                ├─ SUCCESS ──────────┐
       │                │                    │
       │                │                    ▼
       │                │         ┌──────────────────┐
       │                │         │ Store results    │
       │                │         │ Mark success ✓   │
       │                │         └──────────────────┘
       │                │
       │                └─ FAILURE ──────────┐
       │                                     │
       │                                     ▼
       │                          ┌──────────────────┐
       │                          │ Store error      │
       │                          │ Show in UI:      │
       │                          │ • Rubric: ✓      │
       │                          │ • Assessment: ✗  │
       │                          └──────────────────┘
       │
       └─ FAILURE ────────────────┐
                                  │
                                  ▼
                       ┌──────────────────┐
                       │ Store error      │
                       │ Skip assessment  │
                       │ Show in UI:      │
                       │ • Rubric: ✗      │
                       │ • Assessment: -  │
                       └──────────────────┘
```

---

## UI State Machine: NewAssessment Page

```
┌─────────────────────────┐
│      Initial State      │
│  • No images uploaded   │
│  • No models selected   │
│  • Submit disabled      │
└───────┬─────────────────┘
        │
        │ User uploads rubric images
        ▼
┌─────────────────────────┐
│   Rubric Images Ready   │
│  • Submit still disabled│
└───────┬─────────────────┘
        │
        │ User uploads student images
        ▼
┌─────────────────────────┐
│   Student Images Ready  │
│  • Submit still disabled│
└───────┬─────────────────┘
        │
        │ User selects rubric model
        ▼
┌─────────────────────────┐
│   Rubric Model Selected │
│  • Submit still disabled│
└───────┬─────────────────┘
        │
        │ User selects assessment model
        │ (creates first pair)
        ▼
┌─────────────────────────┐
│   Model Pair Created    │
│  • Pair preview shown   │
│  • Submit still disabled│
└───────┬─────────────────┘
        │
        │ User enters questions & grades
        ▼
┌─────────────────────────┐
│     Form Valid          │
│  • Submit ENABLED ✓     │
└───────┬─────────────────┘
        │
        │ User clicks Submit
        ▼
┌─────────────────────────┐
│     Submitting          │
│  • Loading spinner      │
│  • Submit disabled      │
└───────┬─────────────────┘
        │
        │ API success
        ▼
┌─────────────────────────┐
│  Navigate to Dashboard  │
│  • Assessment running   │
└─────────────────────────┘
```

---

## UI State Machine: Review Page (Question Tab)

```
┌─────────────────────────┐
│   Load Assessment Data  │
└───────┬─────────────────┘
        │
        │ Fetch results
        │ Fetch rubric results
        ▼
┌─────────────────────────┐
│   Check Assessment Type │
└───────┬─────────────────┘
        │
        ├─ Legacy (no rubric) ────────┐
        │                             │
        │                             ▼
        │                  ┌─────────────────────┐
        │                  │  Show Single Model  │
        │                  │  • No sub-tabs      │
        │                  │  • Standard display │
        │                  └─────────────────────┘
        │
        └─ New (with rubric) ─────────┐
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │  Show Sub-tabs      │
                           └─────┬───────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Both Tab   │      │ Rubric Tab   │      │ Feedback Tab │
│──────────────│      │──────────────│      │──────────────│
│ • Rubric     │      │ • Rubric     │      │ • Marks      │
│   Response   │      │   Response   │      │ • Feedback   │
│ • Feedback   │      │   ONLY       │      │   ONLY       │
│ • Marks      │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
```

---

## Backward Compatibility Strategy

```
┌─────────────────────────────────────────┐
│   Assessment Creation                   │
└──────┬──────────────────────────────────┘
       │
       ├─ Old Flow (Pre-Rubric) ──────────┐
       │                                  │
       │                                  ▼
       │                       ┌──────────────────┐
       │                       │ Store:           │
       │                       │ • selectedModels │
       │                       │ • No rubric data │
       │                       └────┬─────────────┘
       │                            │
       │                            ▼
       │                       ┌──────────────────┐
       │                       │ Grade with:      │
       │                       │ • Single models  │
       │                       │ • No rubric step │
       │                       └────┬─────────────┘
       │                            │
       │                            ▼
       │                       ┌──────────────────┐
       │                       │ Display:         │
       │                       │ • Legacy UI      │
       │                       │ • No sub-tabs    │
       │                       └──────────────────┘
       │
       └─ New Flow (With Rubric) ─────────┐
                                          │
                                          ▼
                               ┌──────────────────┐
                               │ Store:           │
                               │ • modelPairs     │
                               │ • rubricImages   │
                               └────┬─────────────┘
                                    │
                                    ▼
                               ┌──────────────────┐
                               │ Grade with:      │
                               │ • Rubric first   │
                               │ • Then assess.   │
                               └────┬─────────────┘
                                    │
                                    ▼
                               ┌──────────────────┐
                               │ Display:         │
                               │ • New UI         │
                               │ • Sub-tabs       │
                               └──────────────────┘
```

---

## Key Design Decisions

### 1. Model Pairing Strategy
**Decision:** Indices must match between rubric and assessment selectors

**Rationale:**
- Clear visual relationship
- Easy to understand for users
- Prevents confusion about which models are paired

**Alternative Considered:** Drag-and-drop pairing
- Rejected: Too complex for users
- Rejected: Harder to implement

### 2. Rubric Failure Handling
**Decision:** Fail the entire pair attempt if rubric fails

**Rationale:**
- Assessment quality depends on rubric
- Better to show clear failure than poor results
- User can retry with different model

**Alternative Considered:** Use default/empty rubric
- Rejected: Would produce inconsistent results
- Rejected: Misleading to user

### 3. UI Sub-Tabs Organization
**Decision:** Three sub-tabs: Both, Rubric, Feedback

**Rationale:**
- "Both" is default - most comprehensive view
- "Rubric" for debugging rubric extraction
- "Feedback" for quick grade review

**Alternative Considered:** Single view with collapsible sections
- Rejected: Too cluttered for many model pairs
- Rejected: Harder to scan quickly

---

**Last Updated:** [To be filled]
