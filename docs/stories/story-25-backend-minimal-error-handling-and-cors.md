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

