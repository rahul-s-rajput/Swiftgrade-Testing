# Story 20 — Backend: Sessions and Image Registration (FastAPI)

## Goal
- Provide primitives to start a grading run (session) and register student/answer-key images.

## Scope
- Create sessions.
- Register image URLs with role and order.
- Optional: signed-upload URL issuance for direct object storage uploads.

## Out of Scope
- Grading, results, discrepancies (covered in later stories).
- Authentication beyond permissive CORS for prototype.

## Data Model (Prototype)
- `session(id uuid pk, status text default 'created', created_at, updated_at)`
- `image(id uuid pk, session_id uuid, role text in ['student','answer_key'], url text, order_index int, created_at)`

## API Contracts

1) POST `/sessions`
- Req: `{}`
- Res: `{ "session_id": string, "status": "created" }`

2) POST `/images/register`
- Req:
```json
{
  "session_id": "<uuid>",
  "role": "student" | "answer_key",
  "url": "https://...",
  "order_index": 0
}
```
- Res: `{ "ok": true }`

3) (Optional) POST `/images/signed-url`
- Req: `{ "filename": "student-1.png", "content_type": "image/png" }`
- Res: `{ "uploadUrl": "...", "headers": { ... }, "publicUrl": "..." }`

## Storage (Supabase)
- Use a Supabase Storage bucket, e.g., `grading-images`.
- Modes:
  - Public-read (simplest for prototype), or
  - Private with signed-read URLs (recommended). Ensure signed URL TTL > expected grading duration.
- Persist: `storage_path`, the URL used for prompts (`publicUrl` or signed-read URL), and `role` + `order_index`.

## Upload Flow (Frontend File[] → URL)
- Preferred: Client requests a presigned upload target, then uploads directly, then registers the resulting public/signed URL.
- Steps per file:
  1) POST `/images/signed-url` with `{ filename, content_type }` → returns `{ uploadUrl, headers, publicUrl }`.
  2) Client uploads with given `uploadUrl` and `headers`.
  3) POST `/images/register` with `{ session_id, role, url: publicUrl, order_index }`.
- **Note:** Signed upload URLs expire after 2 hours (non-configurable in Supabase)
- Alternative: For local single-user setup, consider base64 encoding for smaller images

## Idempotency & Ordering
- Idempotent registration per `(session_id, url)`; replays do not create duplicates.
- Recommended DB constraints:
  - UNIQUE `(session_id, url)`
  - UNIQUE `(session_id, role, order_index)` to keep ordering stable
- Require `order_index` to be contiguous per `role` starting at 0.

## Validation
- `session_id` exists.
- `role` in {student, answer_key}.
- `url` is non-empty, HTTPS preferred.
- `order_index` >= 0.

## Acceptance Criteria
- Creating a session returns a UUID and status `created`.
- Registering images persists records tied to session and is idempotent per `(session_id,url)` if retried.
- CORS allows Vite dev origin; JSON errors on bad input.

## Status
Completed on 2025-08-27 (PT). Verified end-to-end: session creation, signed upload URL issuance, file upload to Supabase Storage, and image registration with idempotency and contiguous ordering per role.

## Completed Tasks
- Implemented `POST /sessions` in `app/routers/sessions.py` returning `{ session_id, status: 'created' }`.
- Implemented `POST /images/register` in `app/routers/images.py` with:
  - URL validation (http/https/data).
  - Idempotency by `(session_id, url)`.
  - Slot uniqueness by `(session_id, role, order_index)` with `ORDER_INDEX_TAKEN` error.
  - Contiguous ordering per role starting at 0 with `NON_CONTIGUOUS_ORDER_INDEX` error.
- Implemented `POST /images/signed-url` for Supabase Storage direct uploads, returning `{ uploadUrl, headers, path, publicUrl? }`.
- Added environment variables in `.env.example` (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`, `CORS_ORIGINS`).
- Added Supabase SQL DDL and tested in Supabase project; tables created, uploads functional.

## Implementation Notes
- Endpoints
  - `POST /sessions` → creates a row in `public.session` with generated UUID. See `app/routers/sessions.py`.
  - `POST /images/signed-url` → uses Supabase Python SDK to call `create_signed_upload_url(path)` and `get_public_url(path)`. See `app/routers/images.py`.
  - `POST /images/register` → writes to `public.image` enforcing idempotency and contiguous order. See `app/routers/images.py`.

- Schemas (`app/schemas.py`)
  - `SessionCreateRes`, `ImageRegisterReq`, `SignedUrlReq`, `SignedUrlRes`, `ErrorResponse`.

- SQL DDL (run in Supabase SQL Editor)
```sql
create extension if not exists pgcrypto;

create table if not exists public.session (
  id uuid primary key,
  status text not null default 'created',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.image (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.session(id) on delete cascade,
  role text not null check (role in ('student','answer_key')),
  url text not null,
  order_index int not null check (order_index >= 0),
  created_at timestamptz not null default now(),
  unique (session_id, url),
  unique (session_id, role, order_index)
);

alter table public.session enable row level security;
alter table public.image enable row level security;
```

- Environment
  - `.env` requires: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET` (e.g., `grading-images`), `CORS_ORIGINS`.
  - Bucket can be public for prototype. If private, use signed-read URLs for `url` when registering.

- Testing Notes
  - Health: `GET /health` → `{ ok: true }`.
  - Session: `POST /sessions` returns UUID.
  - Signed upload: `POST /images/signed-url` → `uploadUrl`, `headers`, `path`, `publicUrl?`; then PUT file to `uploadUrl`.
  - Register: `POST /images/register` → `{ ok: true }`; replays idempotent.
  - Errors: bad URL → 400; slot taken → `ORDER_INDEX_TAKEN`; non-contiguous index → `NON_CONTIGUOUS_ORDER_INDEX`.

## Notes for Frontend Alignment
- In `AssessmentContext.addAssessment()` first call POST `/sessions` to obtain id, then upload/register images.
- Image URLs should be public (or signed-read) so LLMs can fetch them during grading.
- For local use: Consider using public bucket for simplicity since it's single-user.
