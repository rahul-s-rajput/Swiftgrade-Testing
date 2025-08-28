# Story 22 — Backend: Async Grading via OpenRouter

## Goal
- Execute async, bounded-concurrency grading across selected models × tries. Persist raw and parsed results.

## Environment
- Requires:
  - `OPENROUTER_API_KEY`
  - Optional: `OPENROUTER_BASE_URL` (defaults to `https://openrouter.ai/api/v1`)

## Inputs
- Session data: images, question set, `human_marks_by_qid` already provided.
- Payload: models and their try counts.

## API Contract
POST `/grade/single`
- Req:
```json
{
  "session_id": "abc123",
  "models": [
    { "name": "openai/gpt-4o", "tries": 2 },
    { "name": "anthropic/claude-3.5-sonnet", "tries": 1 }
  ]
}
```
- Res: `{ "ok": true, "session_id": "abc123" }`

## Behavior
- Build a consistent prompt (system + user with image URLs + question metadata).
- Use `httpx.AsyncClient` and `asyncio.Semaphore(MAX_CONCURRENCY)`.
- Retry 429/5xx with exponential backoff + jitter (e.g., 3 attempts).
- Parse model output to schema:
```json
{
  "answers": [
    { "question_id": "Q1", "marks_awarded": 9, "rubric_notes": "..." },
    { "question_id": "Q2", "marks_awarded": 3, "rubric_notes": "..." }
  ]
}
```
- Persist per `(session_id, question_id, model_name, try_index)`; store `validation_errors` if parsing fails.

### Session status
- Set `session.status = 'grading'` when tasks begin.
- On completion: `session.status = 'graded'` if no fatal error; set `'failed'` if unrecoverable exception.
- Story 26 will expose `GET /sessions/{session_id}` for polling.

## Async Implementation Example
```python
import asyncio
import httpx
from typing import List, Dict

async def grade_with_model(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    model: str,
    messages: List[Dict],
    try_index: int
):
    async with semaphore:  # Limit concurrent requests
        for attempt in range(3):  # Retry logic
            try:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={
                        "model": model,  # e.g., "openai/gpt-4o"
                        "messages": messages,
                        "provider": {"allow_fallbacks": False}
                    },
                    timeout=60.0
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get('retry-after', 60))
                    await asyncio.sleep(retry_after * (2 ** attempt))
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if attempt == 2:  # Last attempt
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

## OpenRouter Request Spec
- Endpoint: `POST https://openrouter.ai/api/v1/chat/completions`
- Headers:
  - `Authorization: Bearer <OPENROUTER_API_KEY>`
  - `HTTP-Referer: <your_app_url>` (optional for local use)
  - `X-Title: <your_app_name>` (optional for local use)
- Body (example, image grading with URL or base64):
```json
{
  "model": "openai/gpt-4o",  // Always use full model name format
  "messages": [
    { "role": "system", "content": "You are a strict grader. Output valid JSON only..." },
    { "role": "user", "content": [
        { "type": "text", "text": "Grade the student's answers against the answer key." },
        // Option 1: URL-based images
        { "type": "image_url", "image_url": { "url": "https://.../student-1.png" } },
        // Option 2: Base64-encoded images (useful for local files)
        { "type": "image_url", "image_url": { "url": "data:image/png;base64,iVBORw0..." } },
        { "type": "text", "text": "Questions: Q1 (max 10), Q2 (max 5)..." }
      ] }
  ],
  // Optional: Add provider routing for reliability
  "provider": {
    "order": ["openai"],  // Single provider for local use
    "allow_fallbacks": false  // Disable for predictable local testing
  }
}
```
- For local single-user: Base64 encoding may be simpler than managing signed URLs
- Model names must use exact OpenRouter format: `provider/model-name`

## Iterations Mapping
- Frontend provides a single `iterations` count. Server accepts either:
  - `{ models: [ { name, tries } ] }` (explicit per-model tries), or
  - `{ models: [ { name } ], default_tries: <number> }` (server expands to per-model tries).
- The UI should map its global `iterations` to `default_tries` when calling this endpoint.

## Data Model
- `result(id, session_id, question_id, model_name, try_index, marks_awarded, rubric_notes, raw_output, validation_errors, created_at)`

## Supabase DDL
```sql
create table if not exists public.result (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.session(id) on delete cascade,
  question_id text not null,
  model_name text not null,
  try_index int not null check (try_index >= 1),
  marks_awarded numeric(10,2),
  rubric_notes text,
  raw_output jsonb,
  validation_errors jsonb,
  created_at timestamptz not null default now(),
  unique (session_id, question_id, model_name, try_index)
);

create index if not exists idx_result_session on public.result(session_id);
```

## Acceptance Criteria
- All model×try tasks are attempted with concurrency cap and bounded retries.
- At least one successful parsed result per model×try is stored or a validation error is recorded.
- Session status transitions to `graded` or `failed` appropriately.
- Handle 429 rate limits with exponential backoff
- Support both URL and base64 image inputs

## Notes
- For local single-user: Consider using base64 for simpler setup without storage buckets
- Model names must use exact format from OpenRouter (e.g., "openai/gpt-4o", not "gpt-4o")
- Implement proper error handling for 429 (rate limit) and 5xx errors

