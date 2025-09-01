# Story 25 — Backend: Minimal Error Handling & CORS

## Goal
- Provide consistent JSON errors and permissive CORS for the prototype.

## Scope
- JSON error handler returning `{ error: { code, message } }` with HTTP status codes.
- CORS configuration for local dev (Vite) - simplified for single user.

## Environment
- `.env`: set `CORS_ORIGINS` to a comma-separated list of allowed origins, e.g.
  - `CORS_ORIGINS=http://localhost:5173,http://localhost:5174`
  - Backend reads this and configures `CORSMiddleware` accordingly.

## Error Envelope
- Shape for all non-2xx responses:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "order_index must be >= 0",
    "details": { "field": "order_index" },
    "correlation_id": "req_12345"
  }
}
```
- `correlation_id` rules:
  - Echo incoming `X-Request-ID` if present; else generate a UUID per request.
  - Include the `correlation_id` in server logs.
- Common codes: `VALIDATION_ERROR`, `NOT_FOUND`, `INTERNAL_ERROR`, `UNAUTHORIZED`.

Backend pointers:
- Error handling implemented centrally in `app/util/errors.py` and registered in `app/main.py`.
- 429 from upstream (OpenRouter) should propagate with `Retry-After` header when possible.

## Acceptance Criteria
- 422 for validation errors with field-level messages.
- 404 for unknown sessions.
- 500 for internal errors with correlation id in logs.
- 429 for rate limit errors from OpenRouter (with retry-after header)
- CORS allows frontend to call from localhost dev port with proper headers exposed.

## Non-Goals
- Comprehensive monitoring or SLOs (not needed for single local user)
- Rate limiting (single user doesn't need this)
- Complex authentication/authorization (local use only)

## CORS Configuration (FastAPI)
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # Vite dev ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # Important for custom headers
)
```

## Status
Completed on 2025-08-28 (PT). Unified JSON error envelope and permissive CORS configured for local dev.

## Completed Tasks
- Centralized error handlers in `app/util/errors.py`:
  - Standard envelope `{ error: { code, message, details, correlation_id } }`.
  - Correlation ID from `X-Request-ID` or generated UUID; logged with each error.
  - Maps common codes: `VALIDATION_ERROR`, `NOT_FOUND`, `UNAUTHORIZED`, `RATE_LIMITED`, `HTTP_ERROR`, `INTERNAL_ERROR`.
  - Propagates headers (e.g., `Retry-After`) from raised `HTTPException`.
- Updated grading router `app/routers/grade.py`:
  - Returns 422 for validation errors via `_bad_request()`.
  - On OpenRouter 429 after retries, raises 429 with `Retry-After` header.
- CORS in `app/main.py` reads `CORS_ORIGINS` from environment and configures `CORSMiddleware` with `expose_headers=["*"]`.
- `.env.example` documents `CORS_ORIGINS` for Vite dev ports.

## Implementation Notes
- Error handlers registered in `app/main.py`:
  - `validation_exception_handler` (422) includes field-level `details.errors` from FastAPI validation.
  - `http_exception_handler` maps codes by status and includes propagated headers.
  - `general_exception_handler` returns 500 with `INTERNAL_ERROR` and logs correlation id.
- CORS origins parsed from `CORS_ORIGINS` (comma-separated) with credentials, all methods/headers, and all exposed headers.

## Testing Notes
- 422: Trigger by sending an invalid payload; expect `error.code=VALIDATION_ERROR` and field errors.
- 404: Request with unknown session; expect `error.code=NOT_FOUND`.
- 429: Force OpenRouter rate limit (or mock); expect 429 with `Retry-After` header surfaced.
- 500: Cause an internal exception; expect `error.code=INTERNAL_ERROR` and correlation id in logs.
- CORS: From `http://localhost:5173` call any endpoint; verify no CORS errors and custom headers accessible.
