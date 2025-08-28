# Story 26 — Backend ↔ Frontend Integration (Prototype)

## Goal
- Replace mocks in `src/context/AssessmentContext.tsx` with live API calls while keeping current UI intact.

## Steps
1) Create session: POST `/sessions` → `session_id`.
2) Upload/register images: POST `/images/register` for each image (or obtain signed URLs first).
3) Configure questions + human marks: POST `/questions/config` with `human_marks_by_qid`.
4) Start grading: POST `/grade/single` with `{ models: [{name, tries}] }`.
5) Poll results + stats until `complete`:
   - GET `/results/{session_id}`
   - GET `/stats/{session_id}`

## Assessment-to-API Mapping (from `AssessmentContext`)
- Inputs:
  - `images: File[]` → For each file, call `/images/signed-url` → upload → `/images/register` with returned `publicUrl` and `order_index`.
  - `questions` and `humanGrades` → Use a JSON editor for direct paste (no parsing). Post the exact JSON to `/questions/config` with `questions[]` and `human_marks_by_qid`.
  - `selectedModels: string[]` and `iterations: number` → Call `/grade/single` with `{ models: selectedModels.map(id => ({ name: id })), default_tries: iterations }`.

## Status & Polling
- Endpoint options:
  - `GET /sessions/{session_id}` → `{ status: created|grading|graded|failed }` (and optional `progress` 0–1).
  - or `GET /grade/status/{session_id}` → same shape.
- Poll either status endpoint until `graded`, then fetch `/results` and `/stats` once. For the prototype, polling `/results` + `/stats` directly is acceptable as in Steps.
- Image signed URLs must remain valid until grading completes.

Example status response
```json
{ "session_id": "abc123", "status": "grading", "progress": 0.4 }
```

## Acceptance Criteria
- `addAssessment()` triggers the sequence and updates status from `running` → `complete` using responses.
- The multi-model selection UI continues to function; pricing/context info remains a dropdown-only visual concern and is not requested from backend.
- The results page can render counts and question lists using `/stats` response.

## Notes
- Respect UI preference for model info (Story 06): backend remains agnostic; frontend formats pricing/context purely in dropdown options.
