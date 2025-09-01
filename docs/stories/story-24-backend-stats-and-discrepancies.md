# Story 24 — Backend: Stats & Discrepancies API

## Goal
- Compute and return all discrepancy metrics for the results page, aligned with the provided table.

## Definitions
- Tag Z/P/F by marks vs max: Z=0, F=max, P=else.
- Range buckets by percent: `0_25` (0–25), `25_74_9` (25.1–74.9), `75_100` (75–100).
- `<100%` set: qids where marks < max.

## API Contract
GET `/stats/{session_id}`
- Res shape:
```json
{
  "session_id": "abc123",
  "human_marks_by_qid": { "Q1": 9, "Q2": 3 },
  "totals": {
    "total_max_marks": 15,
    "total_marks_awarded_by_model_try": {
      "openai/gpt-4o": { "1": 14, "2": 15 },
      "anthropic/claude-3.5-sonnet": { "1": 13 }
    }
  },
  "discrepancies_by_model_try": {
    "openai/gpt-4o": {
      "1": {
        "lt100": { "count": 1, "questions": ["Q2"] },
        "zpf": {
          "count": 1,
          "questions": ["Q1"],
          "mismatched": [{ "qid": "Q1", "human": "P", "ai": "F" }]
        },
        "range": {
          "count": 1,
          "questions": ["Q2"],
          "mismatched": [{ "qid": "Q2", "human": "0_25", "ai": "75_100" }]
        }
      }
    }
  }
}
```

## Supabase Source and Computation
- Read `human_marks_by_qid` from `public.stats` for the session.
- Read AI outputs from `public.result` filtered by `session_id`; aggregate totals and per-model×try metrics in memory for the prototype.
- Recommended index: `create index if not exists idx_result_session on public.result(session_id);`.

## Computation Details
- Build `human_lt100` and `ai_lt100(model,try)` sets; compute symmetric-diff for count and list.
- For Z/P/F and Range, compute tags for human and AI per qid; mismatch if tags differ.
- Include detailed `mismatched` arrays for UI tooltips.

## UI Mapping to Frontend
- Frontend fields per model×try (attempt):
  - `discrepancies100` → length of symmetric-diff set from `<100%` (use `discrepancies_by_model_try[model][try].lt100.count`).
  - `questionDiscrepancies100` → same as above; UI uses identical value for now.
  - `zpfDiscrepancies` → `discrepancies_by_model_try[model][try].zpf.count`.
  - `zpfQuestionDiscrepancies` → same as above; UI uses identical value for now.
  - `rangeDiscrepancies` → `discrepancies_by_model_try[model][try].range.count`.
  - `rangeQuestionDiscrepancies` → same as above; UI uses identical value for now.
  - `totalScore` → `totals.total_marks_awarded_by_model_try[model][try]`.
- Per-model `averages` are arithmetic means across attempts for the above numeric fields.
- Question lists in UI can use `mismatched.questions` arrays for tooltips and drill-ins.

## Acceptance Criteria
- Numbers and lists reflect exact definitions.
- Works even if some questions are missing AI outputs (skip those without AI marks in counts; optionally track missing separately).

## Persistence
- Optionally cache into `stats.discrepancies_by_model_try` and `stats.totals` after grading; recompute on GET for correctness in prototype.

## Status
Completed on 2025-08-28 (PT). Endpoint implemented and wired into FastAPI. Verification with UI occurs after frontend integration.

## Completed Tasks
- Implemented `GET /stats/{session_id}` in `app/routers/stats.py`.
- Added response model `StatsRes` in `app/schemas.py`.
- Wired router in `app/main.py` via `app.include_router(stats_router.router)`.

## Implementation Notes
- Reads human marks from `public.stats.human_marks_by_qid` and question max marks from `public.question`.
- Reads AI outputs from `public.result` filtered by `session_id`.
- Computes:
  - `totals.total_max_marks` as sum of `question.max_marks`.
  - `totals.total_marks_awarded_by_model_try[model][try]` as sum of AI marks across questions.
  - Discrepancies per model×try over qids where AI has marks:
    - `<100%` symmetric-diff between AI `<100%` set and Human `<100%` intersect AI-qids.
    - Z/P/F mismatches comparing `_zpf_tag(human)` vs `_zpf_tag(ai)`.
    - Range mismatches comparing `_range_bucket(human)` vs `_range_bucket(ai)`.
- Rows with `question_id = "__parse_error__"` are ignored.
- No additional environment variables required.

## Testing Notes
- Full testing will be performed after frontend integration (Story 26). For backend smoke test:
  - Ensure `public.stats.human_marks_by_qid`, `public.question`, and `public.result` are populated for a session.
  - Call `GET /stats/{session_id}` and verify `totals` and per model×try discrepancy counts and lists.
