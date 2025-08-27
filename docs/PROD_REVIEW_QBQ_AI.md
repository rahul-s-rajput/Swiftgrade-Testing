# Production Readiness Review — QBQ AI Workflows and Code

Author: Cascade
Date: 2025-08-22

This document reviews the attached workflows (draw.io) and the Python modules:
- `image_prompt_service.py`
- `process_image_prompt_batch_task.py`
- `external_assessment_grading_results_service.py`

It maps flows to code, summarizes strengths/weaknesses, rates production readiness and AI integration, and recommends improvements.

---

## 1) Architecture & Workflow Overview (from diagrams)

### 1.1 Prepare students data for grading on AI
High-level flow:
- Validate inbound request from API → create prompt process in DB → create image entities.
- Build system message with question list; compute token counts; determine `batch_size`.
- Split images into batches respecting per-student pages and token constraints.
- Persist batches; enqueue Celery tasks.

Code mapping:
- Prompt and token accounting: `ImagePromptService._format_system_message()`, `ImagePromptService.process_images_prompts()`.
- Batch size: `ImagePromptService._calculate_batch_size()` using `ImageTokenService` and env caps.
- Batch creation/persistence: `ImagePromptService._create_image_prompt_batches()`.
- Task orchestration: `ImagePromptService.process_images_prompts()` → Celery `chain()` + `group()` + `chord()` of `preprocess_batch` → `process_batch` → `process_batches_results`.

### 1.2 Send batches to LLM
High-level flow:
- For each batch: check tokens/rate limit → wait/retry if not permitted.
- Make request to LLM with schema → process response; save success/failure.

Code mapping:
- Rate limiting & precheck: `preprocess_batch` (Celery task).
- LLM request & retries: `process_batch` → `process_gpt_response()`.
- Persist results: `ImagePromptService.update_completed_prompt()` / `update_failed_prompt()`.

### 1.3 Handle image process batches results
High-level flow:
- Read successful batch results from DB.
- Parse LLM responses into internal schema.
- If at least one success → mark process completed and send parsed data to API; else mark failed and send failure.

Code mapping:
- `ExternalAssessmentGradingResultsService.call()` orchestrates end state and reporting.
- Parsing: `_format_batch_results()` → `__parse_gpt_response_data()`.
- Status updates + API call: `_complete_recognition_results()` / `_fail_recognition_results()` and `_send_results_to_api()`.

### 1.4 AI Module Schemas (diagram)
- Types: `ImagePromptStatus`, `ImagePromptBatchProcessStatus`, `ExternalResultProcessingStatuses`.
- Data schemas: `ImagePromptSchema`, `ImageSchema`, `ImagePromptBatchSchema`, `GPTGradingResultResponseSchema`, external assessment result schemas.
- Code references: imports across all three modules and parsing via `pydantic.parse_obj_as`.

---

## 2) Flow-to-Code Deep Dive with Key Snippets

> Snippets are shown to illustrate current implementation; line numbers may differ slightly across versions.

### 2.1 Batch size and token-aware orchestration (`image_prompt_service.py`)

Batch size calculation with caps tied to output tokens per image and RTG limits:
```python
# image_prompt_service.py
35     def _calculate_batch_size(self, raw_prompt_tokens: int) -> int:
36         """Calculates batch size with RTG limitations applied."""
37         batch_size = self.image_token_service.calculate_batch_size(raw_prompt_tokens)
38 
39         # TODO: use RTG_MAX_BATCH_SIZE as a temporary limit for images amount per request to GPT,
40         # because gpt-4o returns incomplete results if batch size is too big.
41         # https://community.openai.com/t/latest-model-gpt-4o-2024-08-06-reduced-number-of-token-for-result/898760
42         # https://community.openai.com/t/o4-mini-high-and-o3-context-window-issue-and-high-hallucination-rate/1236872
43         if (
44             batch_size * env.OUTPUT_TOKENS_PER_IMAGE > env.RTG_MAX_COMPLETION_TOKENS or
45             batch_size > env.RTG_MAX_BATCH_SIZE
46         ):
47             batch_size = min(floor(env.RTG_MAX_COMPLETION_TOKENS / env.OUTPUT_TOKENS_PER_IMAGE), env.RTG_MAX_BATCH_SIZE)
48         
49         return batch_size
```

End-to-end orchestration and Celery chord fan-in:
```python
# image_prompt_service.py
93         batch_tasks[image_prompt_process_id].extend([
94             chain(
95                 preprocess_batch.si(
96                     image_prompt_process_id,
97                     image_prompt_batch.id,
98                     raw_prompt_tokens + self.image_token_service.tokens_per_image * len(
99                         image_prompt_batch.image_ids),
100                 ),
101                 process_batch.si(image_prompt_batch.id, image_prompt_batch.request_log),
102             )
103             for image_prompt_batch in image_prompt_batches
104         ])
106     for image_prompt_process_id, tasks in batch_tasks.items():
107         chord(group(tasks), process_batches_results.si(image_prompt_process_id)).delay()
```

Batching algorithm respects `pages_per_student` and `batch_size`:
```python
# image_prompt_service.py
202         while i < len(images):
203             if len(current_batch) + pages_per_student <= batch_size:
204                 current_batch.extend(images[i:i + pages_per_student])
205                 i += pages_per_student
206             else:
207                 batches.append(current_batch)
208                 current_batch = []
210         batches.append(current_batch)
```

Message construction with optional model assessment images:
```python
# image_prompt_service.py
223         message = [
224             {
225                 'role': 'system',
226                 'content': system_message,
227             },
228             {
229                 'role': 'user',
230                 'content': [
231                     {'type': 'text', 'text': prompt or ''},
232                     *formatted_images
233                 ]
234             }
235         ]
237         if model_assessment:
238             message[1]['content'].extend([
239                 {'type': 'text', 'text': MODEL_ASSESSMENT_MESSAGE},
240                 *self._format_images(model_assessment)
241             ])
```

### 2.2 Pre-processing and LLM invocation (`process_image_prompt_batch_task.py`)

Token/rate-limit gating (pre-task) with retry or revoke:
```python
# process_image_prompt_batch_task.py
24     try:
25         can_run = check_if_can_run_task(image_prompt_id, image_prompt_batch_process_id, batch_tokens_count)
26     except (GPTRateLimitException, RTGResourceLockException) as rate_limit_error:
29         logger.error(f'{rate_limit_error}\nimage_prompt_batch_process_id: {image_prompt_batch_process_id}')
30         app.control.revoke(self.request.id)
31         return
33     if not can_run:
34         raise self.retry(countdown=60)
```

LLM request with response schema and robust error handling/backoff:
```python
# process_image_prompt_batch_task.py
55         # TODO: Create and pass a response schema for the ChatGPT response(response_format)
56         response = await chat_gpt.ask_chatgpt(
57             RTG_AI_MODEL,
58             messages,
59             RTG_MAX_COMPLETION_TOKENS,
60             RTG_AI_REASONING,
61             RTG_AI_VERBOSITY,
62             RTG_RATE_LIMIT_BUCKET_KEY,
63             GPTGradingResultResponseSchema,
64         )
65     except ChatGptVisionException as e:
66         if self.request.retries < self.max_retries:
67             countdown = (self.request.retries + 1) * 60
68             raise self.retry(exc=e, countdown=countdown)
70         error_message = 'Exceeded number of max allowed retries'
71         await image_prompt_service.update_failed_prompt(image_prompt_batch_process_id, {'error': error_message})
```

Write outcome to storage:
```python
# process_image_prompt_batch_task.py
84     if response.is_error:
85         await image_prompt_service.update_failed_prompt(image_prompt_batch_process_id, response.data)
86     else:
87         await image_prompt_service.update_completed_prompt(image_prompt_batch_process_id, response.data)
```

### 2.3 Batch results aggregation and API reporting (`external_assessment_grading_results_service.py`)

Aggregate successful batches and parse into internal schema:
```python
# external_assessment_grading_results_service.py
44     async def _get_successful_batch_results(self, image_prompt_process_id: int) -> list[ImagePromptBatchSchema]:
45         batch_results = await self.image_prompt_batch_storage.list_objects(
46             image_prompt_process_id=image_prompt_process_id,
47             status=ImagePromptBatchProcessStatus.COMPLETED,
48             order_by="id"
49         )
50         if not batch_results:
51             raise ExternalAssessmentGradingException('No successfully finished batches.')
```

Parsing and failure tolerance:
```python
# external_assessment_grading_results_service.py
71         result = []
73         for batch in batch_results:
74             try:
75                 parsed_response = self.__parse_gpt_response_data(batch)
76             except Exception as exc:  # TODO: replace with more precise exceptions
77                 logger.error(f'Could not parse GPT response. Error: {exc}')
78                 continue
80             result.extend(parsed_response)
82         if not result:
83             raise ExternalAssessmentGradingException('Could not successfully parse at least one batch result')
```

Finalize and send to API:
```python
# external_assessment_grading_results_service.py
118         image_prompt = await self.image_prompt_storage.get_object(id=image_prompt_process_id)
120         return ExternalAssessmentResultSchema(
121             assessment_id=image_prompt.external_assessment_id,
122             assessment_settings_id=image_prompt.external_assessment_settings_id,
123             status=status,
124             data=data or [],
125         )
```

---

## 3) Strengths, Weaknesses, Risks, and Ratings (per component)

### 3.1 `image_prompt_service.py`

- Strengths
  - Clear separation of concerns: token accounting, batching, message building, persistence, and task orchestration.
  - Celery `group/chord` usage enables parallel batch processing with a deterministic fan-in callback.
  - Good type hints and use of Pydantic schemas for strong boundaries.
  - Helpful docstrings and examples for `_split_images_into_batches()`.
  - Practical hard caps (`RTG_MAX_BATCH_SIZE`, `RTG_MAX_COMPLETION_TOKENS`) to avoid model truncation.

- Weaknesses / Risks
  - Token model coupling: `OUTPUT_TOKENS_PER_IMAGE` heuristic can drift from provider behavior; risk of truncation or waste.
  - No explicit idempotency or deduplication keys for batches; re-runs may create duplicates if upstream retries.
  - No tracing/metrics emitted around chord fan-in/outs; limited observability for production incidents.
  - Error path when `pages_per_student > batch_size` marks process failed but doesn’t convey reason back to API at this step.
  - Storage writes assume atomicity; there’s no transaction spanning batch creation + task enqueue (risk of orphan tasks or DB records).

- Ratings
  - Code quality: 8/10
  - Reliability & failure-handling: 7/10
  - Scalability: 8/10
  - Observability: 6/10
  - AI integration soundness: 8/10
  - Overall: 7.6/10

### 3.2 `process_image_prompt_batch_task.py`

- Strengths
  - Explicit pre-run rate limiting and resource lock checks; friendly backoff and revocation on hard limits.
  - Structured retries with exponential-ish backoff for transient LLM errors.
  - Clear separation between Celery task entry points and async response handler.
  - Validation and schema-aware `ask_chatgpt(..., GPTGradingResultResponseSchema)` integration.

- Weaknesses / Risks
  - `app.control.revoke(self.request.id)` comment indicates potential semantic mismatch with result lifecycle; requires stronger guarantees to avoid partial deliveries.
  - Broad exception catch-all logs stringified errors but lacks structured context (batch IDs, model, token counts) as fields.
  - Missing idempotency against duplicate result writes when task retries after network/timeout.
  - No circuit breaker or adaptive rate limit when repeated failures occur.
  - `max_retries=3` may still be high for expensive requests without budget control.

- Ratings
  - Code quality: 7.5/10
  - Reliability & failure-handling: 7/10
  - Scalability: 7.5/10
  - Observability: 6/10
  - AI integration soundness: 8.5/10
  - Overall: 7.3/10

### 3.3 `external_assessment_grading_results_service.py`

- Strengths
  - Good domain service abstraction with clear responsibilities: read, parse, mark status, report.
  - Pydantic-based parsing (`parse_obj_as`) provides strict validation into internal schema.
  - Tolerates partial success (skips malformed batches but still completes if any parsed).

- Weaknesses / Risks
  - Uses a broad `except Exception` during parsing; doesn’t surface which batch failed or why beyond message string.
  - No per-batch error reporting back to API; loses granularity for auditing.
  - Lacks structured metrics (e.g., total batches, parsed count, dropped count) and tracing span.
  - All-or-nothing final status: marks process completed on any success; product requirements may prefer quorum thresholds.

- Ratings
  - Code quality: 7.5/10
  - Reliability & failure-handling: 7/10
  - Scalability: 8/10
  - Observability: 5.5/10
  - AI integration soundness: 7.5/10
  - Overall: 7.1/10

---

## 4) Cross-Cutting Concerns and Production Readiness

- Logging & Observability
  - Current logs are mostly unstructured strings; adopt structured logging (JSON) with consistent fields: `process_id`, `batch_id`, `model`, `tokens_in/out`, `latency_ms`, `retry_count`, `rate_limiter_state`.
  - Emit metrics: success/failure rates, parse error counts, average batch latency, token consumption per batch, chord completion latency.
  - Add tracing spans across API → service → Celery tasks → LLM call → DB writes.

- Idempotency & Exactly-Once Semantics
  - Add `idempotency_key` to each batch (derived from `image_prompt_process_id + image_ids + prompt hash`).
  - Enforce upsert/compare-and-swap on storage updates to avoid double-writes after retries.

- Token Budgeting & Cost Control
  - Track input/output token budgets per assessment; reject or split further when exceeding quotas.
  - Persist model/version and token assumptions with each batch for auditability.

- Rate Limiting & Backpressure
  - `check_if_can_run_task(...)` is a good start; document and expose queue depth, estimated wait, and bucket status.
  - Consider global semaphore to avoid herd effects when many tasks become eligible simultaneously.

- Schema Management
  - Version `GPTGradingResultResponseSchema` and external result schemas. Persist the expected schema version per batch.
  - Optionally use tool-calls/JSON mode with strict response_format to reduce parse errors.

- Error Taxonomy
  - Replace broad `except Exception` with precise custom exceptions (e.g., `ResponseShapeError`, `SchemaValidationError`, `TransportError`).
  - Propagate rich error objects through storage to drive analytics and retries.

- Security & Privacy
  - Avoid logging PII; scrub student names and answers in logs. Keep only identifiers.
  - Ensure presigned URLs (if applicable) and short TTLs for images.
  - Secrets from `settings` must be loaded via environment with rotation support.

- Data Integrity
  - Wrap batch creation + enqueue in a transaction/outbox pattern so tasks are only visible after durable commit.
  - Add state machine constraints to prevent illegal transitions.

- Testing
  - Unit tests for `_split_images_into_batches`, `_prepare_messages`, token math, and parsing in `__parse_gpt_response_data`.
  - Integration tests for Celery chord with in-memory broker, mock LLM service, and storage fakes.

---

## 5) Recommendations (Prioritized)

1) Observability upgrade (high)
- Structured logging + metrics + tracing; dashboards for success rate, latency, tokens, retries.

2) Idempotency and storage invariants (high)
- Idempotency keys for batch writes and updates; dedupe on retries; outbox pattern for Celery enqueue.

3) Response schema hardening (high)
- Use strict JSON response format/tool-calls with a JSON schema matching `GPTGradingResultResponseSchema`.
- Validate at boundary and fail fast with actionable errors.

4) Rate limiter feedback loop (medium-high)
- Expose rate limiter state and add adaptive backoff; add circuit breaker when provider is degraded.

5) Error taxonomy & per-batch reporting (medium)
- Replace broad exceptions; enrich `_format_batch_results()` with batch-level error collection and percentages; send summary to API.

6) Token/cost governance (medium)
- Persist token counts and model versions per batch; build budgets and alerts per assessment.

7) Data lifecycle and compliance (medium)
- TTL policy for `response_log`; redact raw content if not needed post-aggregation.

8) Documentation and runbooks (medium)
- Runbooks for common incidents: provider timeouts, schema drifts, queue backlog.

---

## 6) Production Readiness Scores

- Architecture-Flow alignment: 8/10
- Robustness under load/failures: 7/10
- Observability/operability: 6/10
- Security & privacy posture: 6.5/10
- AI integration quality: 8/10
- Overall Production Readiness: 7.1/10

---

## 7) Quick Wins (Low Effort, High Impact)

- Add `extra` fields to `logger` calls with IDs and counts; ensure every log line includes `image_prompt_process_id` and `image_prompt_batch_process_id`.
- Replace `except Exception` in `_format_batch_results()` with `ValidationError` and a custom `ResponseParseError`.
- Record `tokens_in`, `expected_tokens_out` before calling LLM; attach to storage for cost tracking.
- Add `retry_state` into `response_log` on failures to speed up incident triage.

---

## 8) Open Questions

- What is the required success threshold to consider a process “completed” — any success vs. majority vs. all?
- Does API require per-student error details when parsing fails for some batches?
- Are image URLs presigned, and what’s the retention/TTL policy?
- What broker/result backend and visibility timeout do Celery workers use? Any at-least-once semantics caveats?

---

## 9) Appendix — Component Summaries

- `ImagePromptService`
  - Orchestrates token calculation, batching, message building, batch persistence, Celery graph submission.
- `process_image_prompt_batch_task`
  - Enforces rate limits, invokes LLM with schema, retries on transient errors, updates batch status.
- `ExternalAssessmentGradingResultsService`
  - Aggregates successful batch results, parses to internal DTOs, flips final statuses, and reports back to API.

---

This review aims to provide a practical roadmap to move from a strong prototype to a production-grade, observable, idempotent, and cost-aware AI batch processing pipeline.
