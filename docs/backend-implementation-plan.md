# Backend Implementation Plan (FastAPI + Supabase + OpenRouter)

## Overview
- Single-student prototype for local single-user deployment
- Async calls with bounded concurrency, Supabase for storage + Postgres
- Human grades provided as full JSON map `human_marks_by_qid`
- Simplified architecture without unnecessary complexity for single-user use

## Environment
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OPENROUTER_API_KEY`
- `MAX_CONCURRENCY` (default 5 for single user)
- `CORS_ORIGINS` (dev: http://localhost:5173,http://localhost:5174)

## Directory Structure (proposed)
```
app/
  main.py
  deps.py
  schemas.py
  db.py
  routers/
    sessions.py
    images.py
    questions.py
    grade.py
    results.py
    stats.py
  services/
    openrouter.py
    storage.py
    stats.py
  util/
    errors.py
    logging.py
```

## Supabase Storage Setup (Simplified for Local Use)
- Bucket: `grading-images` (use public bucket for simplicity)
- Mode: public-read for local single-user (no auth complexity needed)
- **Note:** Signed upload URLs expire after 2 hours (non-configurable)
- Alternative: Support base64 image uploads for simpler local workflow
- Endpoints:
  - POST `/images/signed-url` → returns `{ uploadUrl, headers, publicUrl }`
  - POST `/images/register` with `{ session_id, role, url, order_index }`
  - Optional: POST `/images/base64` for direct base64 upload
- Persist both `storage_path` and the URL used in prompts
- Idempotency: de-duplicate on `(session_id, url)`

## DB Schema (DDL sketch)
- See `docs/Essay_Grading_Prototype_Workflow.html` → SQL section, plus fields:
  - `session.status` (created|graded|failed)
  - `stats.human_marks_by_qid jsonb`, `stats.totals jsonb`
  - `result.validation_errors jsonb`

### Tables & Indexes (optimized for single user)
- `image(session_id, role, order_index, url, storage_path, created_at)`
  - UNIQUE `(session_id, url)`
  - UNIQUE `(session_id, role, order_index)` ensures stable ordering per role
- `result(session_id, question_id, model_name, try_index, ...)`
  - UNIQUE `(session_id, question_id, model_name, try_index)`
  - INDEX `(session_id, model_name)` and `(session_id, question_id)`
  - INDEX `(created_at)` for recent results
- `stats(session_id, ...)`
  - PRIMARY KEY `(session_id)`
- `session(id, status, created_at, updated_at)`
  - INDEX `(status)` for filtering
  - INDEX `(created_at)` for recent sessions

## Pydantic Schemas (V2 Syntax)
```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional

class SessionCreateRes(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    session_id: str
    status: str = "created"

class ImageRegisterReq(BaseModel):
    session_id: str
    role: str = Field(..., pattern="^(student|answer_key)$")
    url: str
    order_index: int = Field(..., ge=0)

class QuestionsConfigReq(BaseModel):
    session_id: str
    questions: List[Dict]
    human_marks_by_qid: Dict[str, float]

class ModelConfig(BaseModel):
    name: str  # Must use full format: "provider/model-name"
    tries: int = Field(1, ge=1, le=5)

class GradeSingleReq(BaseModel):
    session_id: str
    models: List[ModelConfig]
    default_tries: Optional[int] = None
```

## UI Input Requirements (JSON paste)
- The frontend must provide a JSON editor/textarea to paste exact payloads for question config:
```json
{
  "session_id": "...",
  "questions": [ { "question_id": "Q1", "number": 1, "max_marks": 10 } ],
  "human_marks_by_qid": { "Q1": 9 }
}
```
- No free-text parsing is supported by the backend.
- Canonical `question_id` convention: `Q<number>`.
- Validation: unique `question_id` per session; marks within `[0, max_marks]`; all human-mark keys present in `questions`.

## Core Algorithms
- Async grading fan-out/fan-in with `asyncio.Semaphore`.
- Backoff on 429/5xx: `sleep(base * 2**attempt + jitter)`.
- Parsing guardrails: JSON schema with fallback to `validation_errors`.
- Discrepancy calculators:
  - `<100%` symmetric diff
  - Z/P/F mismatch by tag
  - Range mismatch by bucket

## OpenRouter Integration Details (Updated)
- Endpoint: `POST https://openrouter.ai/api/v1/chat/completions`
- Headers:
  - `Authorization: Bearer <OPENROUTER_API_KEY>`
  - `HTTP-Referer: <your_app_url>` (optional for local)
  - `X-Title: <your_app_name>` (optional for local)
- Request body supports both URL and base64 images:
```python
{
  "model": "openai/gpt-4o",  # Always use full format
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": [
      {"type": "text", "text": "..."},
      # URL format
      {"type": "image_url", "image_url": {"url": "https://..."}},
      # Base64 format
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    ]}
  ],
  "provider": {
    "order": ["openai"],
    "allow_fallbacks": false  # Disable for local testing
  }
}
```
- Error handling:
  - 429: Extract `retry-after` header, implement exponential backoff
  - 5xx: Retry with backoff, max 3 attempts
- Concurrency: `asyncio.Semaphore(MAX_CONCURRENCY)`
- Use `httpx.AsyncClient` with proper timeout (30-60s)

## Milestones
1) Scaffold API + health + CORS (Story 20)
2) Sessions + Images (Story 20)
3) Questions + Human Marks (Story 21)
4) OpenRouter integration + Grading (Story 22)
5) Results API (Story 23)
6) Stats + Discrepancies (Story 24)
7) Minimal error handling (Story 25)
8) Frontend integration (Story 26)

## Sequence Diagram (text)
- Frontend → POST `/sessions` → `session_id`
- Frontend → POST `/images/register` × N
- Frontend → POST `/questions/config`
- Frontend → POST `/grade/single`
- Frontend → GET `/results/{session_id}` + GET `/stats/{session_id}` (poll until done)

## Session Status & Polling
- Add `GET /sessions/{session_id}` returning `{ status: created|grading|graded|failed, progress?: number }`.
- Optionally `GET /grade/status/{session_id}` equivalent.
- Poll status until `graded`, then fetch `/results` and `/stats` once; prototype may directly poll results/stats as above.
- Update `session.status` transitions: `created` → `grading` (on start) → `graded` or `failed`.

## UI Mapping
- Results UI shape combines data from `/results` and `/stats`:
  - Per-model `attempts[]`: use discrepancy counts from `stats.discrepancies_by_model_try` and totals from `stats.totals`.
  - `averages`: arithmetic mean across attempts for numeric fields.
  - Per-question feedback: derive from parsed `result` rows grouped by `question_id` and `try_index`.
- Optionally expose `GET /results/ui/{session_id}` to serve a ready-to-render payload (see Story 23/24).

## Prompt Strategy (sketch)
- System: role of grader, strict JSON response with schema and examples.
- User: includes ordered student image URLs, answer key image URLs, and question list with `max_marks`.
- Validation: reject if any question missing.

## Error Handling & CORS (Simplified)
- Error envelope for non-2xx:
```json
{ "error": { "code": "VALIDATION_ERROR", "message": "...", "details": {"field": "..."}, "correlation_id": "..." } }
```
- Correlation id: echo `X-Request-ID` or generate UUID per request
- CORS configuration for local dev:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # Important for custom headers
)
```
- Handle OpenRouter specific errors:
  - 429: Rate limit with retry-after
  - 401: Invalid API key
  - 400: Invalid model name format

## Simplified Architecture Notes (Single Local User)
- Use public bucket for images (no auth complexity needed)
- Support base64 images as alternative to URL uploads
- No rate limiting needed (single user)
- No caching needed (single user, low volume)
- No WebSocket needed (polling is fine for single user)
- Basic logging only (console output is sufficient)
- Keep error handling simple but robust for OpenRouter API
- Model names must use exact OpenRouter format: `provider/model-name`

## Python Dependencies
```
fastapi==0.115.0+
uvicorn[standard]
pydantic==2.0+
supabase==2.0+
httpx
python-multipart
python-dotenv
```
