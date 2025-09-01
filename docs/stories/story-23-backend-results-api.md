# Story 23 — Backend: Results API

## Goal
- Provide a read API to fetch parsed results grouped for UI rendering.

## API Contract
GET `/results/{session_id}`
- Res:
```json
{
  "session_id": "abc123",
  "results_by_question": {
    "Q1": {
      "openai/gpt-4o": [
        { "try_index": 1, "marks_awarded": 9, "rubric_notes": "Good" },
        { "try_index": 2, "marks_awarded": 10, "rubric_notes": "Excellent" }
      ],
      "anthropic/claude-3.5-sonnet": [
        { "try_index": 1, "marks_awarded": 8, "rubric_notes": "Okay" }
      ]
    },
    "Q2": { ... }
  }
}
```

## Supabase Source and Aggregation
- Read from `public.result` filtered by `session_id`.
- Group by `question_id`, then `model_name`, sorting by `try_index` ascending.
- When parse failed and only `validation_errors` exist, omit the entry or return an empty array for that model (consistent with Acceptance Criteria below).

## UI Adapter Guidance
- The frontend `AssessmentResults` type expects, per model, an `attempts[]` array with counts and per-question feedback, plus `averages` and a `questions` array.
- Two approaches:
  1) Keep this endpoint as-is and let the frontend context combine `/results/{session_id}` with `/stats/{session_id}` to compute UI fields.
  2) Add a companion endpoint `GET /results/ui/{session_id}` that returns a UI-ready payload shaped as:
```json
{
  "questions": [{ "number": 1, "text": "..." }, ...],
  "modelResults": [
    {
      "model": "openai/gpt-4o",
      "averages": {
        "discrepancies100": 1,
        "questionDiscrepancies100": 1,
        "zpfDiscrepancies": 1,
        "zpfQuestionDiscrepancies": 1,
        "rangeDiscrepancies": 1,
        "rangeQuestionDiscrepancies": 1,
        "totalScore": 14
      },
      "attempts": [
        {
          "attemptNumber": 1,
          "discrepancies100": 1,
          "questionDiscrepancies100": 1,
          "zpfDiscrepancies": 1,
          "zpfQuestionDiscrepancies": 1,
          "rangeDiscrepancies": 1,
          "rangeQuestionDiscrepancies": 1,
          "totalScore": 14,
          "questionFeedback": [ { "questionNumber": 1, "feedback": "...", "mark": "9/10" } ]
        }
      ]
    }
  ]
}
```
- Mapping details are defined in Story 24.

## Acceptance Criteria
- Matches grouping in `docs/Essay_Grading_Prototype_Workflow.html`.
- Empty arrays returned where a model/try had parse errors (or omit the model entirely if no successes).
- Fast and deterministic for a single session size.

## Notes
- This endpoint is read-only and should not require any additional environment variables.
- Index recommended: `create index if not exists idx_result_session on public.result(session_id);` (see Story 22 DDL).

## Frontend Alignment
- Use this endpoint to render per-question panels and per-model try chips.

## Status
Completed on 2025-08-28 (PT). Endpoint implemented and wired into FastAPI. End-to-end verification will occur after frontend integration.

## Completed Tasks
- Implemented `GET /results/{session_id}` in `app/routers/results.py`.
- Added response models in `app/schemas.py` (`ResultItem`, `ResultsRes`).
- Wired router in `app/main.py` via `app.include_router(results_router.router)`.

## Implementation Notes
- Reads `public.result` filtered by `session_id` and selects `question_id, model_name, try_index, marks_awarded, rubric_notes`.
- Groups into `results_by_question[question_id][model_name] = [ResultItem...]`.
- Sorted by `try_index` ascending.
- Rows with `question_id = "__parse_error__"` (parse failures) are omitted, so models with no successes may be omitted entirely for that question (consistent with Acceptance Criteria).
- No additional environment variables required.

## Testing Notes
- Full testing will be performed after frontend integration (Story 26). For backend-only smoke test:
  - Ensure grading results exist in `public.result` for a session.
  - Call `GET /results/{session_id}` and verify grouping and sorting.
