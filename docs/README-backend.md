# Backend (FastAPI) — Story 20 Sessions & Images

Implements:
- POST `/sessions` → `{ "session_id": string, "status": "created" }`
- POST `/images/register` → `{ "ok": true }` (idempotent per `(session_id,url)` and enforces contiguous `order_index` per role)
- POST `/images/signed-url` → issues a Supabase Storage signed upload URL for direct browser upload
- GET `/health` → `{ ok: true }`

Persistence uses Supabase Postgres via the Supabase Python Client SDK (no direct psycopg/SQLAlchemy connection). Images will be stored in Supabase Storage in later steps.

## Environment (.env)

Create a `.env` file (see `.env.example`) with:

```
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_STORAGE_BUCKET=grading-images
CORS_ORIGINS=http://localhost:5173,http://localhost:5174
OPENROUTER_API_KEY=your_openrouter_api_key
# Optional (defaults to https://openrouter.ai/api/v1)
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Notes:
- Get the project URL from Supabase → Project Settings → API.
- Use the Service Role key for server-side DB/Storage actions in the backend only (do not expose it to the browser).
- Create the `SUPABASE_STORAGE_BUCKET` in Supabase Storage (e.g., `grading-images`). You can choose public-read for simplicity.

## Quickstart (Windows PowerShell)

```powershell
# 1) Create and activate venv
py -m venv .venv
. .\.venv\Scripts\Activate.ps1

# 2) Install deps (Supabase SDK included)
pip install -r requirements-backend.txt

# 3) Start server (port 8000)
uvicorn app.main:app --reload --port 8000
```

Optional: set custom CORS origins
```powershell
$env:CORS_ORIGINS = "http://localhost:5173,http://localhost:5174"
```

## Notes
- Idempotency: registering the same `(session_id,url)` returns `{ ok: true }` without duplicates.
- Contiguous ordering: for a given `(session_id, role)`, `order_index` must equal the current count (0-based). If a slot for the same `(role, order_index)` already exists with a different URL, a `400` is returned.
- Error envelope for non-2xx responses uses shape:
```json
{ "error": { "code": "...", "message": "...", "details": { ... }, "correlation_id": "..." } }
```

## Supabase Schema (run in SQL Editor)

Create tables and constraints (RLS can remain enabled; backend uses service role key):

```sql
-- Enable uuid generation if needed
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

-- Optional RLS policies (backend uses service role and bypasses RLS)
alter table public.session enable row level security;
alter table public.image enable row level security;
```

### Additional Schema (Stories 21–24)

```sql
-- Questions configured per session
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

-- Stats cache per session (human marks + computed aggregates)
create table if not exists public.stats (
  session_id uuid primary key references public.session(id) on delete cascade,
  human_marks_by_qid jsonb not null default '{}'::jsonb,
  totals jsonb,
  discrepancies_by_model_try jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Grading results per model try and question
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

## Supabase Storage — Signed Uploads

Endpoint: `POST /images/signed-url`

Request
```json
{ "filename": "student-1.png", "content_type": "image/png" }
```

Response
```json
{
  "uploadUrl": "https://<proj>.supabase.co/storage/v1/object/upload/sign/grading-images/<uuid>/student-1.png?token=...",
  "token": "...", // optional, included when available
  "path": "<uuid>/student-1.png",
  "headers": { "Content-Type": "image/png" },
  "publicUrl": "https://<proj>.supabase.co/storage/v1/object/public/grading-images/<uuid>/student-1.png"
}
```

Client Upload (fetch example)
```ts
await fetch(uploadUrl, { method: 'PUT', headers, body: file });
```

Then register the image
```json
POST /images/register
{ "session_id": "<uuid>", "role": "student", "url": "<publicUrl>", "order_index": 0 }
```

Notes
- Signed upload URLs are valid for ~2 hours (Supabase default).
- If your bucket is private, `publicUrl` may be null; you can use `createSignedUrl` for reads or make the bucket public for the prototype.
- RLS: Signed upload tokens allow inserting the object; the backend uses the service role to mint the token.

## Next Stories
- Story 21: questions + human marks
- Story 22: grading via OpenRouter
- Story 23/24: results and stats
- Story 25: improved error handling and CORS tweaks
- Story 26: frontend integration
