# QBQ AI System — Simple, Plain‑English Review

Author: Cascade
Date: 2025-08-22

This document explains, in everyday language, how the QBQ AI grading system works, what each main Python file does, what’s good, what could be better, and what to fix first. It is a simplified companion to `PROD_REVIEW_QBQ_AI.md`.

---

## What the system does (big picture)
- You send student answer images to the AI module.
- The system breaks the images into small groups (batches) so they fit within AI limits.
- Each batch is sent to the AI model for grading.
- When all batches are done, the system collects the results, converts them to the expected format, and sends them back to your main API.

---

## The three main flows in everyday terms

### 1) Prepare student data
- Build a “system message” for the AI (what the AI should do and how to answer).
- Count tokens (roughly the size/complexity of the request) and decide a safe batch size.
- Split images into batches based on how many pages each student has and the batch size.
- Save those batches and queue background jobs to process them.

Where this happens in code:
- `image_prompt_service.py` → `process_images_prompts()`, `_calculate_batch_size()`, `_create_image_prompt_batches()`

### 2) Send batches to the AI
- For each batch, first check if we’re allowed to call the AI now (rate limits).
- If not allowed, wait and try again later.
- If allowed, send the message (text + images) to the AI.
- Store success or failure for that batch.

Where this happens in code:
- `process_image_prompt_batch_task.py` → `preprocess_batch` (rate limit check)
- `process_image_prompt_batch_task.py` → `process_batch` and `process_gpt_response()` (actual AI call and saving results)

### 3) Collect and send results back
- Read all successful batches from the database.
- Convert the AI output into the system’s standard format.
- Mark the whole job as completed (or failed if nothing could be parsed).
- Send the final result to the main API.

Where this happens in code:
- `external_assessment_grading_results_service.py` → `call()` (orchestration) and helpers

---

## What each file is responsible for

### `image_prompt_service.py`
- Chooses batch size based on token math and safety limits from settings.
- Splits images into batches that match student page counts.
- Builds messages for the AI (system instructions + user text + images, and optionally model comparison images).
- Starts background tasks using Celery (`chain`, `group`, `chord`) so many batches run in parallel.

### `process_image_prompt_batch_task.py`
- Background tasks that:
  - Check rate limits and resource locks before running.
  - Call the AI with the messages.
  - Retry on temporary errors with a delay.
  - Save success or failure for each batch.

### `external_assessment_grading_results_service.py`
- After batches finish, pick up the successful ones.
- Parse/validate the AI’s response into your expected data shapes (using Pydantic schemas).
- Mark the overall process as done or failed.
- Send the final data to your API.

---

## Why the design is good (strengths)
- **Clear roles**: Each file has a focused job. Easier to understand and maintain.
- **Respects AI limits**: Token counting and batch sizing avoid oversized requests.
- **Parallel processing**: Many batches can run at the same time; faster overall.
- **Schema validation**: Responses are validated so bad AI output is caught early.
- **Retries and backoff**: Temporary AI errors don’t crash the system; tasks retry.

---

## Where it can fail or confuse (weaknesses and risks)
- **Logging is basic**: Logs are plain text. Hard to search or make dashboards.
- **Duplicate writes**: If a task retries, it might write the same result twice (no idempotency keys).
- **Limited visibility**: No metrics (success rate, latency, token usage) or tracing to quickly debug issues.
- **Partial success policy**: If only some batches succeed, the whole process is marked done. You may want a threshold (e.g., at least 80%).
- **Token estimates can drift**: The estimate for tokens per image may differ from the AI provider’s real behavior.
- **Privacy**: Be careful not to log personal data in plaintext.

---

## Simple ratings (1–10)
- **`image_prompt_service.py`**: 8 for structure, 7 for reliability, 8 for scale, 6 for visibility, 8 for AI use. Overall: **7.6/10**
- **`process_image_prompt_batch_task.py`**: 7.5 structure, 7 reliability, 7.5 scale, 6 visibility, 8.5 AI use. Overall: **7.3/10**
- **`external_assessment_grading_results_service.py`**: 7.5 structure, 7 reliability, 8 scale, 5.5 visibility, 7.5 AI use. Overall: **7.1/10**
- **Whole system overall**: **7.1/10** (strong foundation, needs better visibility and idempotency)

---

## What to fix first (prioritized to-do list)
1) **Better logs and metrics**
   - Use structured (JSON) logs with fields like `process_id`, `batch_id`, `model`, `tokens_in`, `latency_ms`, `retry_count`.
   - Add metrics: success/failure rates, average times, token usage.

2) **Idempotency (no duplicates)**
   - Give each batch an `idempotency_key` (depends on process id + image ids + prompt hash) and make updates upsert-safe.
   - Use an outbox pattern so tasks are only enqueued after the database commit.

3) **Stricter AI responses**
   - Ask the AI to return strict JSON that matches your schema. Reject and retry if not valid.

4) **Smarter rate limiting**
   - When the provider is busy, back off more aggressively or open a “circuit breaker” to avoid wasting calls.

5) **Clearer error types**
   - Replace `except Exception` with specific error classes (e.g., `ResponseShapeError`, `SchemaValidationError`).
   - Save error details (type, where it happened) for reporting.

6) **Privacy & data lifecycle**
   - Avoid logging names or answers; use IDs instead. Consider purging raw AI responses after aggregation.

---

## Short glossary
- **Token**: A tiny chunk of text. AI models limit tokens per request and per response.
- **Batch**: A small group of images sent to the AI in one request so we stay within limits.
- **Chord/Group/Chain (Celery)**: Ways to run many background tasks in parallel, then run a final step when all finish.
- **Schema**: A data blueprint that defines the exact fields and types expected.
- **Idempotency**: Doing the same action twice should not create duplicate records or double-send results.

---

## Quick example of the system’s flow
1) `image_prompt_service.py` calculates batch size and creates batches.
2) Celery runs `preprocess_batch` (checks limits) then `process_batch` (calls AI).
3) Results are saved: success or failure per batch.
4) `external_assessment_grading_results_service.py` collects successes, converts them to the final format, and posts to your API.

---

If you want, I can next add structured logging and idempotency keys to the code to reach production-grade reliability and observability.
