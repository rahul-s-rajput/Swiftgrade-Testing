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
- Body (example, image grading with Supabase Storage URLs only):
```json
{
  "model": "openai/gpt-4o",  // Always use full model name format
  "messages": [
    { "role": "system", "content": "You are a strict grader. Output valid JSON only..." },
    { "role": "user", "content": [
        { "type": "text", "text": "Grade the student's answers against the answer key." },
        // URL-based images hosted in Supabase Storage (public or signed URLs)
        { "type": "image_url", "image_url": { "url": "https://<project>.supabase.co/storage/v1/object/public/grading-images/<path>/student-1.png" } },
        { "type": "text", "text": "Questions: Q1 (max 10), Q2 (max 5)..." }
      ] }
  ],
  // Optional: Add provider routing for reliability
  "provider": {
    "order": ["openai"],  // Single provider for local use
    "allow_fallbacks": false  // Disable for predictable local testing
  },
  // Optional: Reasoning configuration for models that support it (e.g., OpenAI o3-series)
  "reasoning": { "effort": "medium" }
}
```
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
- Images are provided via Supabase Storage URLs (public or signed); base64 inputs are not used

## Notes
- Use Supabase Storage for hosting images referenced in prompts. Prefer public buckets for simplicity during prototyping or generate signed URLs.
- Model names must use exact format from OpenRouter (e.g., "openai/gpt-4o", not "gpt-4o").
- Implement proper error handling for 429 (rate limit) and 5xx errors.


## Status
Completed on 2025-08-28 (PT). Backend implementation finished and wired into FastAPI. End-to-end testing is deferred until frontend integration in a later story.

## Completed Tasks
- Implemented `POST /grade/single` in `app/routers/grade.py` with:
  - Async `httpx` calls, bounded concurrency via `asyncio.Semaphore`.
  - Retries with exponential backoff for 429/5xx.
  - URL-only images (Supabase Storage URLs) in `messages[].content[]` — base64 not used.
  - Optional OpenRouter `reasoning` parameter passed at top-level when provided.
  - Session status transitions: `grading` → `graded`/`failed`.
  - Persistence into `public.result` with conflict on `(session_id, question_id, model_name, try_index)`.
- Added schemas in `app/schemas.py`:
  - `GradeModelSpec`, `GradeSingleReq` (with optional `reasoning`), `GradeSingleRes`.
- Wired router in `app/main.py` via `app.include_router(grade_router.router)`.
- Documented OpenRouter request spec to use Supabase URLs only and where to set `reasoning`.

## Implementation Notes
- Endpoint: `POST /grade/single` in `app/routers/grade.py`.
- OpenRouter call: `POST {OPENROUTER_BASE_URL}/chat/completions` with headers `Authorization: Bearer <OPENROUTER_API_KEY>` and JSON body `{ model, messages, provider.allow_fallbacks=false, reasoning? }`.
- Messages are built from `public.image` (roles: `student`, optional `answer_key`) and `public.question` metadata; images are referenced by URL only.
- Results persisted to `public.result` with `raw_output` and `validation_errors` if parsing fails.
- Env vars in `.env`: `OPENROUTER_API_KEY`, optional `OPENROUTER_BASE_URL`, `GRADING_MAX_CONCURRENCY`.
- Supabase client in `app/supabase_client.py` is used for data access.

## Testing Notes
- End-to-end testing will be performed after frontend integration (Story 26). Until then, backend smoke tests are optional and deferred. When testing:
  - Ensure images are uploaded to Supabase Storage and registered via `POST /images/register`.
  - Ensure questions and `human_marks_by_qid` are configured via `POST /questions/config`.
  - Call `POST /grade/single` with models and optional `reasoning`; verify `public.result` rows.

