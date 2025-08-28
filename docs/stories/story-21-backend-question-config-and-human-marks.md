# Story 21 — Backend: Question Config + Human Marks JSON

## Goal
- Submit question metadata and full human grading for all questions to drive later stats.

## Change vs Previous Plan
- Replace `low_score_question_ids` with `human_marks_by_qid: { [question_id]: number }`.

## Data Model
- `question(id, session_id, question_id, number, max_marks, created_at)`
- `stats(session_id pk, human_marks_by_qid jsonb, totals jsonb, discrepancies_by_model_try jsonb, created_at, updated_at)`
## Supabase DDL
```sql
-- Ensure pgcrypto is enabled once in your project
create extension if not exists pgcrypto;

create table if not exists public.question (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.session(id) on delete cascade,
  question_id text not null,
  number int not null check (number >= 1),
  max_marks numeric(10,2) not null check (max_marks >= 0),
  created_at timestamptz not null default now(),
  unique (session_id, question_id),
  unique (session_id, number)
);

create table if not exists public.stats (
  session_id uuid primary key references public.session(id) on delete cascade,
  human_marks_by_qid jsonb not null default '{}'::jsonb,
  totals jsonb,
  discrepancies_by_model_try jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

## API Contract
POST `/questions/config`
- Req:
```json
{
  "session_id": "abc123",
  "questions": [
    { "question_id": "Q1", "number": 1, "max_marks": 10 },
    { "question_id": "Q2", "number": 2, "max_marks": 5 }
  ],
  "human_marks_by_qid": { "Q1": 9, "Q2": 3 }
}
```
- Res: `{ "ok": true }`

## UI Input Requirement (JSON paste)
- For the prototype, the UI must provide a JSON editor/textarea where the user pastes the exact structures required by this endpoint:
  - `questions`: `[ { question_id: "Q1", number: 1, max_marks: 10 }, ... ]`
  - `human_marks_by_qid`: `{ "Q1": 9, "Q2": 3 }`
- No free-text parsing is supported by the backend.
- Canonical `question_id` convention: `Q<number>` (e.g., `Q1`, `Q2`), matching the UI numbering.
- Ensure `max_marks` are explicitly provided in the pasted JSON.

## Validation
- All `questions[].question_id` are unique within session.
- Every key in `human_marks_by_qid` exists in `questions[]`.
- `0 <= mark <= max_marks` for each question.

## Persistence
- Upsert `question` rows keyed by `(session_id, question_id)`; also enforce uniqueness on `(session_id, number)`.
- Optionally delete questions for the session that are not present in the new payload (treat payload as authoritative).
- Upsert into `public.stats` for the session, replacing `human_marks_by_qid` entirely; update `updated_at`.

## Acceptance Criteria
- Invalid qids or out-of-range marks yield `422` with explanation.
- On success, subsequent stories can read `human_marks_by_qid` to compute discrepancies.

## Frontend Alignment
- Add a textarea or JSON editor that posts `human_marks_by_qid` as JSON for all questions (not only non-100%).

