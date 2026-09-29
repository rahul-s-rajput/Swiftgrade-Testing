# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A desktop app for **testing and comparing AI models' grading of student assessments**. Teachers upload images of student papers + answer keys, pick a set of OpenRouter models, and the app grades each question across all models/tries, then compares AI marks against human benchmark marks. It is a model-benchmarking harness, not a production grading tool.

Stack: **React + TypeScript (Vite)** frontend, **FastAPI (Python)** backend, **Tauri (Rust)** desktop wrapper, **Supabase** (Postgres + Storage) for persistence, **OpenRouter** as the multi-model LLM gateway.

## Building the desktop app (most important)

After **any** change, the desktop app is rebuilt with these 4 steps, in order, from the repo root (Windows, `.venv` active). Skipping a step ships stale code — backend changes in particular only reach the app via steps 1–2.

```bat
:: 0. Bump the version first (see below)
:: 1. Build the backend sidecar exe
pyinstaller backend_launcher.spec --clean
:: 2. Copy it to where Tauri expects the sidecar
copy dist\backend-x86_64-pc-windows-msvc.exe src-tauri\binaries\backend-x86_64-pc-windows-msvc.exe
:: 3. Build the frontend
npm run build
:: 4. Build the Tauri bundle (installers land in src-tauri/target/debug/bundle/{nsis,msi}/)
cd src-tauri && cargo tauri build --debug
```

(Source of truth: `docs/build_instructions.md`.) Frontend-only changes still need steps 3–4; backend-only changes still need all four.

**Bump the version for every new build.** Keep these in sync (currently `1.1.0`):
- `package.json` → `"version"`
- `src-tauri/Cargo.toml` → `version`
- `src-tauri/tauri.conf.json` → `"version"`
- `src-tauri/Cargo.lock` updates itself on the next cargo build

The About dialog reads the version from the build (`package_info().version`), and CI release names come from `package.json`.

After building, sanity-check the sidecar by hitting a real route (e.g. `/debug/routes`), not just `/health`: if `app.main` fails to import inside the exe, `backend_launcher.py` silently falls back to a stub app that only serves `/health` and `/`. `backend_launcher.spec` does not list Supabase-stack hiddenimports, so this is a real risk.

## Commands

```bash
# Frontend dev server (Vite, port 5173) — does NOT start the backend
npm run dev

# Full desktop app in dev (Tauri builds frontend + spawns backend sidecar)
npm run tauri:dev

# Run the FastAPI backend standalone (needed when using `npm run dev` in browser mode)
uvicorn app.main:app --reload --port 8000
# (requires the .venv activated and requirements-backend.txt installed)

npm run lint           # ESLint over the frontend
npm run build          # vite build → dist/ (NO tsc type-check; run `npx tsc -p tsconfig.app.json --noEmit` for that)

npm run backend:build  # = pyinstaller backend_launcher.spec --clean (step 1 above; does NOT copy the exe)
npm run tauri:build    # release-profile tauri build (step 4 without --debug)

# Python tests (ad-hoc scripts, not a configured pytest suite — run individually)
python tests/test_backend.py
python tests/test_reasoning.py
```

There is no automated Python test runner configured; the `tests/*.py` and root-level `test_*.py` / `verify_*.py` files are standalone scripts you run directly with `python`.

Several `package.json` scripts are dead because their target files no longer exist: `build:desktop*`, `clean`, `verify:backend` (`build_desktop_app.py`), `package:all` (`build_app.py`), `backend:build:all` (`scripts/build-backends.js`). The other PyInstaller specs (`backend_fixed.spec`, `backend-x86_64-pc-windows-msvc.spec`), `backend_packager.py`, `backend.py`, and `src-tauri/tauri.conf.debug.json` (Tauri v1 schema) are also stale — `backend_launcher.spec` is the only live spec.

## Environment

Copy `.env.example` → `.env`. Required: `OPENROUTER_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`. Useful knobs: `GRADING_MAX_CONCURRENCY` (default 4), `OPENROUTER_DEBUG=1` (verbose API logging), `GRADE_LOG_DIR` (per-session request/response logs).

In the packaged app, Tauri's `save_env_config` (SetupWizard, first run) writes `.env` to the Tauri app-data dir for identifier `com.swiftgrade.testing.assistant` (`%APPDATA%\com.swiftgrade.testing.assistant\.env` on Windows), and `start_backend` passes that path to the sidecar as `ENV_FILE_PATH`, which is checked first. The Python fallbacks used when `ENV_FILE_PATH` is unset (`load_environment()` in `app/main.py`, `setup_environment()` in `backend_launcher.py`) and `grade.py`'s default log dir (`_default_log_dir()`) still point at the old `com.markgrading.assistant` directory.

## Architecture

### Three-process model
1. **Tauri/Rust (`src-tauri/src/lib.rs`)** owns the window and lifecycle. On startup the frontend calls the `start_backend` Tauri command, which spawns the PyInstaller-compiled FastAPI backend as a **sidecar** on a dynamically chosen port, then returns that port to the frontend. Rust also handles process-tree cleanup (`taskkill /F /T` on Windows) so the Python server dies with the app.
2. **FastAPI backend (`app/`)** does all grading orchestration and talks to OpenRouter + Supabase.
3. **React frontend (`src/`)** is the UI. `src/utils/api.ts` holds a mutable `API_BASE`; `App.tsx` calls `setApiBase()` with the live backend port after the sidecar starts. In browser-only mode (`window.__TAURI__` undefined) it falls back to `http://127.0.0.1:8000`.

### Backend layout (`app/`)
- `main.py` — app factory, CORS (permissive for localhost + `tauri://localhost`), logging middleware that captures full request/response bodies, health/debug endpoints (`/health`, `/health/detailed`, `/debug/routes`, `/debug/info`), and router registration.
- `routers/` — one module per resource: `sessions`, `images`, `questions`, `grade`, `results`, `stats`, `settings`. **`grade.py` is the core** (~2000 lines) and where most grading logic lives.
- `schemas.py` — Pydantic request/response models. Note the **legacy vs. new** split: `models` (flat list) is legacy; `model_pairs` (rubric model + assessment model) is the current path. Both are still supported.
- `supabase_client.py` — single shared `supabase` client built from the service-role key. The app uses the Supabase **client SDK directly**, not SQLAlchemy (`db.py` is dormant/unused).
- `util/json_parser.py` — tolerant LLM-output parsing; `util/errors.py` — exception handlers returning the `{error: {code, message, details}}` envelope the frontend expects.

### The grading flow (two-phase, in `grade.py`)
`POST /grade/single` drives everything. For each model pair × try:
1. **Rubric phase** (`_build_rubric_messages` → `_call_rubric_llm`): the *rubric model* looks at the grading-rubric/answer-key images and produces a rubric text.
2. **Assessment phase** (`_build_messages` → `_call_openrouter`): the *assessment model* grades the student images using that rubric, returning JSON marks per question.

Work items are fanned out with `asyncio` bounded by `GRADING_MAX_CONCURRENCY`. LLM JSON output is notoriously messy, so parsing goes through `_repair_json_string` / `_parse_model_output` / `parse_llm_json_response`, and the system deliberately accepts **many response shapes and field-name aliases** (`marks_awarded`/`mark`/`score`, `question_id`/`qid`/`question`, top-level `results`/`grades`/`answers`, etc. — see README "Flexible Field Names"). Per-model **reasoning** config and per-call **token usage** are captured and persisted.

Results land in Supabase tables: `session`, `image`, `result` (per-question marks), `rubric_result` (phase-1 output), and `token_usage`. `results.py`/`stats.py` read these back; the Review page compares AI marks vs. `human_marks_by_qid`.

### Frontend pages (`src/pages/`)
`Home` (session list) → `NewAssessment` (upload images, configure questions/models, kick off grading) → `Review/:id` (per-question model-vs-human comparison, token-usage tooltips) → `Settings` (API keys, prompt templates, response-schema templates). `AssessmentContext` holds cross-page state. `SetupWizard` runs on first launch to write `.env`.

## Database migrations

SQL migrations live in `app/migrations/` (numbered, each with a `_ROLLBACK.sql`). **They are applied manually**, normally by pasting the SQL into the Supabase SQL Editor (or via the `run_migration.py` / `verify_schema.py` helpers). There is no auto-migration on startup — see `app/migrations/README.md`. Additional ad-hoc schema SQL also lives in `scripts/sql/`.

## Conventions & gotchas

- **Model-pair vs. legacy models**: `grade.py` hardcodes `use_model_pairs = True`, so only `model_pairs` drives grading. A request without pairs (e.g. the frontend's `retryAssessment`, which still sends the legacy `models`) falls back to the pairs stored in `session.model_pairs`; the flat `models` payload itself is ignored, and the legacy persistence branch is dead code. On the read side, older sessions only have `rubric_models`/`assessment_models`, so the frontend still maps both shapes when loading.
- Identity is inconsistent across files: Tauri product name "Swiftgrade Testing Assistant" with identifier `com.swiftgrade.testing.assistant`; npm/crate name `mark-grading-assistant`; Python fallback paths, log dir and CI release title still say `com.markgrading.assistant` / "Mark Grading Assistant". Changing the Tauri identifier moves the app-data dir, so existing users lose their `.env`. Any rename needs to be deliberate and update both the Rust and Python sides together.
- Claude model IDs are auto-prefixed with `anthropic/` for OpenRouter inside `grade.py` if missing — keep that behavior in mind when adding provider handling.
- **Supabase free-plan limits (0.5 GB DB, 1 GB storage, 5 GB egress)** were hit once, and the project was restricted. Keep it lean:
  - Result rows store `raw_output = NULL`. Only `__parse_error__` rows and `rubric_result` keep a trimmed copy (`_slim_response` in `grade.py`). Full responses go to the local session logs in `GRADE_LOG_DIR`. Never write full OpenRouter bodies to the DB: `reasoning_details` holds large encrypted blobs.
  - Uploads are content-addressed at `{role}/{sha256}.{ext}` (`/images/signed-url` with `content_hash`, which returns `exists: true` to skip the upload). The frontend compresses images first (`src/utils/imageUpload.ts`, toggle in Settings → Storage & Usage). Files can be shared between sessions (template reuse), so `DELETE /sessions/{id}` only removes storage files that no other session's `image` rows reference.
  - `GET /usage` (needs migration 006's `get_usage_stats()`) feeds the Home warning banner and the Settings meters. Limits can be overridden with `SUPABASE_DB_LIMIT_MB`, `SUPABASE_STORAGE_LIMIT_MB` and `USAGE_WARN_PERCENT`.
  - One-time cleanup tools: `scripts/sql/cleanup_raw_output.sql` and `python scripts/cleanup_storage.py [--delete]` (dry run by default).
- `src/pages/Review_BACKUP.tsx` contains only the text "BACKUP CREATED" (a placeholder, not real code); `Review.tsx` is the live page. Likewise `FileUploadHTML5.tsx` is the live upload component — `FileUpload.tsx` and `hooks/useTauriDragDrop.ts` are unused.
- The repo root has many one-off docs (`BUGFIX_README.md`, `ERROR_FIXES.md`, `QUICK_FIX_GUIDE.md`, `docs/`) describing past fixes and the rubric architecture — useful background, but treat them as historical, not authoritative on current code.
